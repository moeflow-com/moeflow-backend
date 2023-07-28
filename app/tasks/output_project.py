"""
导出项目
"""
import json
import os
import re
import oss2
import shutil
from zipfile import ZipFile

from app import FILE_PATH, TMP_PATH, celery

from app.constants.output import OutputStatus, OutputTypes
from app.constants.file import FileType
from app import oss
from app.models import connect_db
from app.regexs import SAFE_FILENAME_REGEX
from . import SyncResult
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@celery.task(name="tasks.output_project_task")
def output_project_task(output_id):
    """
    压缩整个项目

    :param project_id: 项目ID
    :return:
    """
    from app.models.file import File
    from app.models.project import Project
    from app.models.output import Output
    from app.models.team import Team
    from app.models.target import Target
    from app.models.user import User

    (File, Project, Team, Target, User)
    oss_file_prefix = celery.conf.app_config["OSS_FILE_PREFIX"]
    connect_db(celery.conf.app_config)
    oss.init(celery.conf.app_config)
    # 获取项目
    output: Output = Output.objects(id=output_id).first()
    if output is None:
        return f"跳过：导出不存在，Output {output_id}"
    project = output.project
    target = output.target
    type = output.type
    file_ids_include = output.file_ids_include
    file_ids_exclude = output.file_ids_exclude

    safe_project_set_name = re.sub(SAFE_FILENAME_REGEX, "□", project.project_set.name)
    safe_project_name = re.sub(SAFE_FILENAME_REGEX, "□", project.name)
    download_name = (
        ("" if project.project_set.default else (safe_project_set_name + " - "))
        + safe_project_name
        + " - "
        + target.language.i18n_name
    )

    # 各个文件夹/文件路径
    zip_tmp_folder_name = str(output.id)  # 临时文件夹名
    zip_name = str(output.id) + ".zip"  # 压缩文件名（和文件夹同名，并都存在zips根目录）
    zip_download_name = download_name + ".zip"
    txt_name = str(output.id) + ".txt"  # 翻译文本名（当仅导出翻译文本的时候使用）
    txt_download_name = download_name + ".txt"
    # PS脚本和其资源文件夹 原位置
    ps_script_path = os.path.abspath(
        os.path.join(FILE_PATH, "ps_script", "ps_script.jsx")
    )
    ps_script_res_folder_path = os.path.abspath(
        os.path.join(FILE_PATH, "ps_script", "ps_script_res")
    )
    # tmp中存放zip的临时文件夹
    zips_tmp_folder_path = os.path.abspath(os.path.join(TMP_PATH, "zips"))
    # 压缩文件路径
    zip_path = os.path.abspath(os.path.join(zips_tmp_folder_path, zip_name))
    zip_tmp_folder_path = os.path.abspath(
        os.path.join(zips_tmp_folder_path, zip_tmp_folder_name)
    )

    zip_ps_script_path = os.path.abspath(
        os.path.join(zip_tmp_folder_path, "ps_script.jsx")
    )
    zip_ps_script_res_folder_path = os.path.abspath(
        os.path.join(zip_tmp_folder_path, "ps_script_res")
    )
    zip_images_folder_path = os.path.abspath(
        os.path.join(zip_tmp_folder_path, "images")
    )
    zip_translations_txt_path = os.path.abspath(
        os.path.join(zip_tmp_folder_path, "translations.txt")
    )
    zip_errors_txt_path = os.path.abspath(
        os.path.join(zip_tmp_folder_path, "errors.txt")
    )
    project_json_path = os.path.abspath(
        os.path.join(zip_tmp_folder_path, "project.json")
    )

    errors = ""
    try:
        # 创建图片临时文件夹
        os.makedirs(zip_images_folder_path, exist_ok=True)
        # 导出 Labelplus 翻译文本
        output.update(status=OutputStatus.TRANSLATION_OUTPUTING)
        labelplus = project.to_labelplus(
            target=target,
            file_ids_include=file_ids_include,
            file_ids_exclude=file_ids_exclude,
        )
        with open(zip_translations_txt_path, "w", encoding="utf-8") as txt:
            txt.write(labelplus)
        if type == OutputTypes.ONLY_TEXT:
            # 上传txt到oss
            output.update(file_name=txt_download_name)
            with open(zip_translations_txt_path, "rb") as txt:
                oss.upload(
                    os.path.join(
                        celery.conf.app_config["OSS_OUTPUT_PREFIX"], str(output.id)
                    )
                    + "/",
                    txt_download_name,
                    txt,
                    headers={"Content-Disposition": f'attachment;"'.encode("utf8")},
                )
        elif type == OutputTypes.ALL:
            output.update(status=OutputStatus.DOWNLOADING)
            # 创建项目信息文件
            project_json = project.to_output_json()
            project_json["output_id"] = str(output.id)
            project_json["output_language"] = target.language.code
            with open(project_json_path, "w", encoding="utf-8") as json_file:
                json.dump(project_json, json_file)
            # 下载项目图片
            files = project.files(
                type_only=FileType.IMAGE,
                file_ids_include=file_ids_include,
                file_ids_exclude=file_ids_exclude,
            )
            for file in files:
                file_path = os.path.abspath(
                    os.path.join(zip_images_folder_path, file.name)
                )
                try:
                    oss.download(
                        oss_file_prefix,
                        file.save_name,
                        local_path=file_path,
                    )
                except oss2.exceptions.NoSuchKey:
                    errors += (
                        f"File {file.name}<{str(file.id)}> is not found in server.\r\n"
                    )
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    logger.exception(Exception)
                    errors += f"File {file.name}<{str(file.id)}> download error.\r\n"
                    if os.path.exists(file_path):
                        os.remove(file_path)
            # 放入PS脚本和其资源文件夹
            # if os.path.exists(ps_script_path):
            #     shutil.copy(ps_script_path, zip_ps_script_path)
            # if os.path.exists(ps_script_res_folder_path):
            #     shutil.copytree(
            #         ps_script_res_folder_path, zip_ps_script_res_folder_path
            #     )
            # 记录错误
            if errors:
                with open(zip_errors_txt_path, "w") as txt:
                    txt.write(
                        f"Project Name: {project.name}\r\n"
                        + f"Project ID:   {str(project.id)}\r\n"
                        + f"Target ID:    {str(target.id)}\r\n"
                        + f"Output ID:    {str(output.id)}\r\n"
                        + "------------------------\r\n"
                    )
                    txt.write(errors)
            # 压缩临时文件夹
            output.update(status=OutputStatus.ZIPING)
            with ZipFile(zip_path, "w") as zip_file:
                for dirpath, dirnames, filenames in os.walk(zip_tmp_folder_path):
                    for filename in filenames:
                        file_path = os.path.abspath(os.path.join(dirpath, filename))
                        file_in_zip_path = os.path.relpath(
                            file_path, zip_tmp_folder_path
                        )
                        zip_file.write(file_path, file_in_zip_path)
            # 上传zip到oss
            with open(zip_path, "rb") as zip_file:
                output.update(file_name=zip_download_name)
                oss.upload(
                    os.path.join(
                        celery.conf.app_config["OSS_OUTPUT_PREFIX"], str(output.id)
                    )
                    + "/",
                    zip_download_name,
                    zip_file,
                    headers={"Content-Disposition": f'attachment;"'.encode("utf8")},
                )
    except Exception:
        output.update(status=OutputStatus.ERROR)
        logger.exception(Exception)
        return (
            f"失败：导出 Project<{str(project.id)}> "
            + f"Target<{str(target.id)}> Output<{str(output.id)}>"
        )
    finally:
        # 删除临时文件夹和zip
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(zip_tmp_folder_path):
            shutil.rmtree(zip_tmp_folder_path)
    output.update(status=OutputStatus.SUCCEEDED)
    return (
        f"成功：导出 Project<{str(project.id)}> "
        + f"Target<{str(target.id)}> Output<{str(output.id)}>"
    )


def output_project(output_id, /, *, run_sync=False):
    alive_workers = celery.control.ping()
    if len(alive_workers) == 0 or run_sync:
        # 同步执行
        output_project_task(output_id)
        return SyncResult()
    else:
        # 异步执行
        return output_project_task.delay(output_id)
