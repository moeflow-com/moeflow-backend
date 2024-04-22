"""
对上传的文件进行预处理
"""

import datetime
import math
from io import BytesIO
from typing import BinaryIO, List, Optional
from uuid import uuid4

import requests
from app import celery, gs_vision, oss
from app.constants.file import FileType, ImageOCRPercent, ParseErrorType, ParseStatus
from app.models import connect_db
from app.tasks import SyncResult
from app.utils.logging import logger
from PIL import Image, ImageDraw
from PIL.Image import Image as ImageCls


class AboutToShutdownError(Exception):
    pass


class MergeImagesError(Exception):
    pass


class OverGoogleVisionLimitError(Exception):
    pass


IMAGE_SPACE = 50  # 图片间距


def get_middle(point1, point2):
    """获取两个点的中点"""
    return (point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2


def get_label_position(
    first_symbol_vertices,
    second_symbol_vertices,
    image_x_start,
    image_x_end,
    image_y_start,
    image_y_end,
):
    image_width = image_x_end - image_x_start + 1
    image_height = image_y_end - image_y_start + 1
    # 文本起始方向
    sorted_points = sorted(first_symbol_vertices, key=lambda v: v[0])
    left_points = sorted_points[0:2]
    right_points = sorted_points[2:4]
    sorted_left_points = sorted(left_points, key=lambda v: v[1])
    sorted_right_points = sorted(right_points, key=lambda v: v[1])
    top_left = sorted_left_points[0]
    bottom_left = sorted_left_points[1]
    top_right = sorted_right_points[0]
    bottom_right = sorted_right_points[1]

    point_x, point_y = get_middle(top_left, top_right)
    # 距离第一个字符的 padding，避免直接标记到文字上导致魔棒取色错误
    first_symbol_padding = 2
    point_y -= first_symbol_padding
    if second_symbol_vertices:
        first_symbol_middle_x, first_symbol_middle_y = get_middle(
            top_left, bottom_right
        )
        second_symbol_middle_x, second_symbol_middle_y = get_middle(
            second_symbol_vertices[0], second_symbol_vertices[2]
        )
        if first_symbol_middle_x != second_symbol_middle_x:
            radian = math.atan2(
                second_symbol_middle_x - first_symbol_middle_x,
                second_symbol_middle_y - first_symbol_middle_y,
            )
            angle = radian * (180 / math.pi)
            if -180 < angle < -45:  # 从右开始
                point_x, point_y = get_middle(top_right, bottom_right)
                point_x += first_symbol_padding
            elif 45 < angle < 180:  # 从左开始
                point_x, point_y = get_middle(top_left, bottom_left)
                point_x -= first_symbol_padding
    # 转换成百分比位置
    x = round(point_x / image_width, 6)
    y = round(point_y / image_height, 6)
    # 经过 first_symbol_padding 偏移可能会超出图片
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    if x > 1:
        x = 1
    if y > 1:
        y = 1
    return {"x": x, "y": y, "point_x": point_x, "point_y": point_y}


def filter_and_parse_blocks(
    blocks, image_x_start, image_x_end, image_y_start, image_y_end
):
    filtered_blocks = []
    for block in blocks:
        vertices = [
            (vertice.get("x", 0), vertice.get("y", 0))
            for vertice in block["boundingBox"]["vertices"]
        ]
        exceed = False
        for vertice in vertices:
            x = vertice[0]
            y = vertice[1]
            if x < image_x_start - IMAGE_SPACE / 2:
                exceed = True
                break
            if x > image_x_end + IMAGE_SPACE / 2:
                exceed = True
                break
            if y < image_y_start - IMAGE_SPACE / 2:
                exceed = True
                break
            if y > image_y_end + IMAGE_SPACE / 2:
                exceed = True
                break
        if exceed:
            continue
        filtered_blocks.append(
            parse_block(block, image_x_start, image_x_end, image_y_start, image_y_end)
        )
    return filtered_blocks


def limit_vertices(vertices, image_x_start, image_x_end, image_y_start, image_y_end):
    vertices = [(vertice.get("x", 0), vertice.get("y", 0)) for vertice in vertices]
    limited_vertices = []
    width = image_x_end - image_x_start + 1
    height = image_y_end - image_y_start + 1
    for vertice in vertices:
        x = vertice[0] - image_x_start
        y = vertice[1] - image_y_start
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > width:
            x = width
        if y > height:
            y = height
        limited_vertices.append((x, y))
    return limited_vertices


def parse_block(block, image_x_start, image_x_end, image_y_start, image_y_end):
    # 块中文字
    block_text = ""
    # 获取第一二个字符，用于标记位置
    first_symbol_vertices = None
    second_symbol_vertices = None
    block_vertices = limit_vertices(
        block["boundingBox"]["vertices"],
        image_x_start,
        image_x_end,
        image_y_start,
        image_y_end,
    )
    symbols_vertices = []
    # 循环段落
    for paragraph in block["paragraphs"]:
        words = paragraph["words"]
        # 循环单词
        for word in words:
            symbols = word["symbols"]
            # 循环字符
            for symbol in symbols:
                symbol_vertices = limit_vertices(
                    symbol["boundingBox"]["vertices"],
                    image_x_start,
                    image_x_end,
                    image_y_start,
                    image_y_end,
                )
                symbols_vertices.append(symbol_vertices)
                if first_symbol_vertices is None:
                    first_symbol_vertices = symbol_vertices
                else:
                    if second_symbol_vertices is None:
                        second_symbol_vertices = symbol_vertices
                block_text += symbol["text"]
                # 如果检测到末尾空格则加上
                breakType = (
                    symbol.get("property", {})
                    .get("detectedBreak", {})
                    .get("type", None)
                )
                if breakType in ["LINE_BREAK", "EOL_SURE_SPACE"]:
                    block_text += "\n"
                if breakType in ["SPACE", "SURE_SPACE"]:
                    block_text += " "
    label_position = get_label_position(
        first_symbol_vertices,
        second_symbol_vertices,
        image_x_start,
        image_x_end,
        image_y_start,
        image_y_end,
    )
    return {
        "text": block_text,
        "vertices": block_vertices,
        "symbols_vertices": symbols_vertices,
        "label_position": label_position,
    }


def merge_images(im1: ImageCls, im2: ImageCls) -> Optional[ImageCls]:
    new_im = None
    try:
        im1_width, im1_height = im1.size
        im2_width, im2_height = im2.size
        total_width = im1_width + im2_width
        max_height: int = max(im1_height, im2_height)
        new_im = Image.new("RGB", (total_width + IMAGE_SPACE, max_height))
        new_im.paste(im1, (0, 0))
        new_im.paste(im2, (im1_width + IMAGE_SPACE, 0))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise MergeImagesError() from e
    return new_im


def merge_images_with_limit(
    images: List, image_files: List[BinaryIO], merged_image_file: BinaryIO
):
    if len(images) != len(image_files):
        raise Exception("images数量和图片文件数量，不匹配")
    if merged_image_file:
        image_files = [merged_image_file, *image_files]
        images = ["LAST_IMAGE", *images]
    [image_file0, *image_files] = image_files
    [image0, *images] = images
    merged_im = Image.open(image_file0)
    images_data = [
        {
            "image": image0,
            "image_x_start": 0,
            "image_x_end": merged_im.size[0] - 1,
            "image_width": merged_im.size[0],
            "image_y_start": 0,
            "image_y_end": merged_im.size[1] - 1,
            "image_height": merged_im.size[1],
        }
    ]
    for i, image in enumerate(images):
        im = Image.open(image_files[i])
        new_im = merge_images(merged_im, im)
        if new_im:
            images_data.append(
                {
                    "image": image,
                    "image_x_start": merged_im.size[0] + IMAGE_SPACE,
                    "image_x_end": merged_im.size[0] + IMAGE_SPACE + im.size[0] - 1,
                    "image_width": im.size[0],
                    "image_y_start": 0,
                    "image_y_end": im.size[1] - 1,
                    "image_height": im.size[1],
                }
            )
            merged_im = new_im
        else:
            raise OverGoogleVisionLimitError()
    merged_image_file = BytesIO()
    merged_im.save(merged_image_file, "png")
    if (
        merged_im.size[0] * merged_im.size[1]
    ) >= 75000000 or merged_image_file.tell() >= 20 * 1024 * 1024:
        raise OverGoogleVisionLimitError()
    return {
        "merged_im": merged_im,
        "merged_image_file": merged_image_file,
        "images_data": images_data,
    }


def google_vision(image_file: BinaryIO):
    image_file.seek(0)
    ocr_api_url = celery.conf.app_config["GOOGLE_OCR_API_URL"]
    http_proxy = celery.conf.app_config.get("GOOGLE_HTTP_PROXY")
    reverse_proxy_auth = celery.conf.app_config.get("GOOGLE_REVERSE_PROXY_AUTH")
    gs_vision_tmp_prefix = ""
    gs_vision_tmp_gs_url = celery.conf.app_config["GOOGLE_STORAGE_MOEFLOW_VISION_TMP"][
        "GS_URL"
    ]
    gs_vision_tmp_image_name = str(uuid4())  # 临时使用用来图像识别的随机名称
    gs_vision_tmp_image_url = (
        gs_vision_tmp_gs_url + "/" + gs_vision_tmp_prefix + gs_vision_tmp_image_name
    )
    gs_vision_tmp_image_blob = None
    json_data = None
    ocr_data = None
    try:
        gs_vision_tmp_image_blob = gs_vision.upload(
            gs_vision_tmp_prefix, gs_vision_tmp_image_name, image_file
        )
        # OCR 请求参数
        request_data = {
            "requests": [
                {
                    "image": {"source": {"imageUri": gs_vision_tmp_image_url}},
                    "features": [{"type": "TEXT_DETECTION"}],
                }
            ]
        }
        # 连接谷歌API
        # 设置代理
        proxies = None
        if http_proxy:
            proxies = {"http": http_proxy, "https": http_proxy}  # 设置代理
        # 设置反向代理验证
        auth = None
        if reverse_proxy_auth and "googleapis.com" not in ocr_api_url:
            auth = reverse_proxy_auth
        result = requests.post(
            ocr_api_url,
            json=request_data,
            proxies=proxies,
            auth=auth,
            timeout=80,
        )
        json_data = result.json()
        # 处理返回的数据
        response = json_data["responses"][0]  # 第一个图片返回的数据
        if "error" in response:
            # OCR服务器报错
            raise Exception(
                f'OCR 服务器报错：{response["error"]}，imageUrl: {gs_vision_tmp_image_url}'
            )
        if len(response.get("fullTextAnnotation", {}).get("pages", [])) == 0:
            ocr_data = {"blocks": []}
        else:
            ocr_data = response["fullTextAnnotation"]["pages"][0]
    except Exception as e:
        logger.error(e, exc_info=True)
        logger.error(json_data)
        raise e
    finally:
        try:
            if gs_vision_tmp_image_blob:
                gs_vision_tmp_image_blob.delete()
        except Exception as e:
            # 删除错误打印异常
            logger.error("删除临时图片出错")
            logger.error(e, exc_info=True)
    return ocr_data


def _draw(im, blocks):
    draw = ImageDraw.Draw(im)
    for block in blocks:
        block_data = parse_block(block, 0, im.size[0], 0, im.size[1])
        label_position = block_data["label_position"]
        for symbol_vertices in block_data["symbols_vertices"]:
            draw.line(
                symbol_vertices,
                fill=(128, 128, 0, 40),
            )
        # draw.line(
        #     block_data["vertices"], fill=(128, 128, 128, 20),
        # )
        # 标记点
        draw.line(
            [
                (
                    label_position["point_x"] - 1,
                    label_position["point_y"] - 1,
                ),
                (
                    label_position["point_x"] + 1,
                    label_position["point_y"] - 1,
                ),
                (
                    label_position["point_x"] + 1,
                    label_position["point_y"] + 1,
                ),
                (
                    label_position["point_x"] - 1,
                    label_position["point_y"] + 1,
                ),
                (
                    label_position["point_x"] - 1,
                    label_position["point_y"] - 1,
                ),
            ],
            fill=128,
        )
    im.show()


class ErrorCounts:
    def __init__(self) -> None:
        self.counts = {}

    def get(self, id, error_name):
        if self.counts.get(id) is None:
            return 0
        if self.counts.get(id).get(error_name) is None:
            return 0
        return self.counts[id][error_name]

    def inc(self, id, error_name, step=1):
        if self.counts.get(id) is None:
            self.counts[id] = {error_name: step}
        else:
            if self.counts.get(id).get(error_name) is None:
                self.counts[id][error_name] = step
            else:
                self.counts[id][error_name] += step


def merge_and_ocr(parsing_images, /, *, parse_alone=False):
    if 2 > 1:
        raise NotImplementedError("OCR under reconstruction")
    if not parsing_images:
        return
    oss_file_prefix = celery.conf.app_config["OSS_FILE_PREFIX"]
    image_error_counts = ErrorCounts()
    parsing_alone_images = []
    team = parsing_images[0].project.team
    while len(parsing_images) > 0:
        merged_image_file = None
        merged_images_data = []
        while len(parsing_images) > 0:
            images_group_count = 1 if parse_alone else 5
            downloading_images = parsing_images[0:images_group_count]
            parsing_images = parsing_images[images_group_count:]
            image_files = []
            merging_images = []
            for downloading_image in downloading_images:
                downloading_image.update(image_ocr_percent=ImageOCRPercent.DOWALOADING)
                # 从 OSS 下载图片（重试）
                while (
                    image_error_counts.get(
                        str(downloading_image.id), "oss_download_error"
                    )
                    < 3
                ):
                    try:
                        image_file = BytesIO(
                            oss.download(
                                oss_file_prefix, downloading_image.save_name
                            ).read()
                        )
                        image_files.append(image_file)
                        merging_images.append(downloading_image)
                        break
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        image_error_counts.inc(
                            str(downloading_image.id), "oss_download_error"
                        )
                else:
                    logger.error(
                        f"ImageFile<{str(downloading_image.id)}> 下载失败且超过重试次数"
                    )
                    downloading_image.update(
                        parse_status=ParseStatus.PARSE_FAILED,
                        parse_error_type=ParseErrorType.IMAGE_CAN_NOT_DOWNLOAD_FROM_OSS,
                    )
            try:
                for merging_image in merging_images:
                    merging_image.update(image_ocr_percent=ImageOCRPercent.MERGING)
                try:
                    merge_data = merge_images_with_limit(
                        merging_images, image_files, merged_image_file
                    )
                except OverGoogleVisionLimitError:
                    # 第一次合并就超限，则让这些图片都单独处理
                    if len(merged_images_data) == 0:
                        if parse_alone:
                            for merging_image in merging_images:
                                merging_image.update(
                                    parse_status=ParseStatus.PARSE_FAILED,
                                    parse_error_type=ParseErrorType.IMAGE_TOO_LARGE,
                                )
                        else:
                            for merging_image in merging_images:
                                merging_image.update(
                                    image_ocr_percent=ImageOCRPercent.WAITING_PARSE_ALONE  # noqa: E501
                                )
                                parsing_alone_images.append(merging_image)
                    else:
                        parsing_images = merging_images + parsing_images
                    break
                new_merged_image_file = merge_data["merged_image_file"]
                new_images_data = merge_data["images_data"]
                merged_image_file = new_merged_image_file
                if len(merged_images_data) == 0:
                    merged_images_data = new_images_data
                else:
                    merged_images_data = [*merged_images_data, *new_images_data[1:]]
                for merging_image in merging_images:
                    merging_image.update(image_ocr_percent=ImageOCRPercent.OCRING)
            except Exception as e:
                logger.error(e, exc_info=True)
                for merging_image in merging_images:
                    if parse_alone:
                        merging_image.update(
                            parse_status=ParseStatus.PARSE_FAILED,
                            parse_error_type=ParseErrorType.IMAGE_PARSE_ALONE_ERROR,
                        )
                    else:
                        merging_image.update(
                            image_ocr_percent=ImageOCRPercent.WAITING_PARSE_ALONE,
                        )
                        parsing_alone_images.append(merging_image)
                break
            if parse_alone:
                break
        # 第一次合并就失败，没有生成合并图片，跳过处理后续图片
        if merged_image_file is None:
            continue
        ocr_connection_error_times = 0
        while ocr_connection_error_times < 3:
            try:
                ocr_data = google_vision(merged_image_file)
                team.update(inc__ocr_quota_google_used=1)
                break
            except Exception:
                ocr_connection_error_times += 1
                logger.error(f"OCR 出错，重试第 {ocr_connection_error_times} 次")
        else:
            logger.error(f"OCR 出错超过 {ocr_connection_error_times-1} 次，停止尝试")
            for merging_image in merging_images:
                merging_image.update(
                    parse_status=ParseStatus.PARSE_FAILED,
                    parse_error_type=ParseErrorType.IMAGE_OCR_SERVER_DISCONNECT,
                )
            continue
        for image_data in merged_images_data:
            image = image_data["image"]
            image.update(image_ocr_percent=ImageOCRPercent.LABELING)
            blocks_data = filter_and_parse_blocks(
                ocr_data["blocks"],
                image_data["image_x_start"],
                image_data["image_x_end"],
                image_data["image_y_start"],
                image_data["image_y_end"],
            )
            for block_index, block_data in enumerate(blocks_data):
                text = block_data["text"]
                x = block_data["label_position"]["x"]
                y = block_data["label_position"]["y"]
                vertices = block_data["vertices"]
                # 创建原文
                same_position_source = image.sources().filter(x=x, y=y).first()
                if same_position_source is None:
                    image.create_source(
                        text,
                        x=x,
                        y=y,
                        machine=True,
                        rank=block_index,
                        vertices=vertices,
                    )
            # 将File设置成处理成功，并清理task_id/开始时间/解析次数/错误类型
            image.update(
                parse_status=ParseStatus.PARSE_SUCCEEDED,
                image_ocr_percent=ImageOCRPercent.FINISHED,
                unset__parse_times=1,
                unset__parse_task_id=1,
                unset__parse_start_time=1,
                unset__parse_error_type=1,
            )
            # 记录OCR限额
            team.update(inc__ocr_quota_used=1)
    if not parse_alone:
        return parsing_alone_images


@celery.task(name="tasks.ocr_task")
def ocr_task(type, id):
    """
    调用谷歌文本识别API，解析图片中的文件，并转化成Source

    :param type: ocr 类型（project/image）
    :param id: 项目/图片 ID
    :return:
    """
    from app.models.project import Project
    from app.models.team import Team

    (Project, Team)
    connect_db(celery.conf.app_config)
    oss.init(celery.conf.app_config)
    gs_vision.init(celery.conf.app_config)
    project = Project.objects(id=id).first()
    if project is None:
        return f"跳过 (项目不存在)：<{type}>{id}"
    if project.ocring:
        return f"跳过 (已在 OCR)：<{type}>{id}"
    queuing_images = project.files(type_only=FileType.IMAGE).filter(
        parse_status=ParseStatus.QUEUING
    )
    if queuing_images.count() == 0:
        return f"跳过 (没有排队中的文件)：<{type}>{id}"
    # TODO 现在可以一下启动很多项目，即使限额不够。需要检查限额并多加一个超限额的错误类型。
    project.update(ocring=True)
    parsing_images = [*queuing_images]
    queuing_images.update(
        parse_status=ParseStatus.PARSING,
        image_ocr_percent=ImageOCRPercent.QUEUING,
        parse_start_time=datetime.datetime.utcnow(),
        unset__parse_error_type=1,
    )
    try:
        parsing_alone_images = merge_and_ocr(parsing_images)
        merge_and_ocr(parsing_alone_images, parse_alone=True)
        project.update(ocring=False)
        return f"成功：<{type}>{id}"
    except AboutToShutdownError:
        return f"Celery 将要关闭，停止标记 <{type}>{id}"
    except Exception as e:
        project.update(ocring=False)
        project.files(type_only=FileType.IMAGE).filter(
            parse_status=ParseStatus.PARSING
        ).update(
            parse_status=ParseStatus.PARSE_FAILED,
            parse_error_type=ParseErrorType.UNKNOWN,
        )
        logger.error(e, exc_info=True)
        return f"失败：<{type}>{id}，错误内容：{e}"


def ocr(type: str, id: str, /, *, run_sync=False):
    if run_sync:
        ocr_task(type, id)
        return SyncResult
    else:
        return ocr_task.apply_async((type, id))


def recover_ocr_tasks():
    """恢复因为 Celery 重启所停止的 tasks"""
    from app.models.file import File
    from app.models.project import Project

    logger.info("-" * 50)
    # 恢复图片
    parsing_images = File.objects(
        type=FileType.IMAGE,
        parse_status=ParseStatus.PARSING,
    )
    logger.info(f"共 {parsing_images.count()} 张图片已恢复 QUEUING")
    parsing_images.update(parse_status=ParseStatus.QUEUING)
    # 恢复项目
    ocring_projects = Project.objects(ocring=True)
    recovering_projects = [*ocring_projects]
    logger.info(f"共 {ocring_projects.count()} 个项目需要恢复 OCR")
    ocring_projects.update(ocring=False)
    for project in recovering_projects:
        id = str(project.id)
        ocr("project", id)
        logger.info(f"已恢复 OCR Project<{id}>：")
