"""
对上传的文件进行预处理
"""
import datetime
import re
import uuid

import chardet
from aliyunsdkcore import client
from aliyunsdkcore.profile import region_provider
from aliyunsdkcore.request import RoaRequest
from celery.exceptions import MaxRetriesExceededError
from flask import json

from app import celery
from app import oss
from app.models import connect_db
from app.constants.file import (
    FileNotExistReason,
    FileSafeStatus,
    FileType,
    FindTermsStatus,
    ParseErrorType,
    ParseStatus,
)
from app.utils.logging import logger
from . import SyncResult


@celery.task(name="tasks.parse_text_task", time_limit=1200)
def parse_text_task(file_id, old_revision_id=None):
    """
    将文本解析成Source

    :param file_id: 传入File的Id(str or ObjectId)
    :param old_revision_id: 旧修订版Id，有的话，会将旧修订版翻译导入其中
    :return:
    """
    from app.models.file import File
    from app.models.project import Project
    from app.models.team import Team
    from app.models.user import User

    (Project, Team, User)
    # 配置
    oss_file_prefix = celery.conf.app_config["OSS_FILE_PREFIX"]
    connect_db(celery.conf.app_config)
    oss.init(celery.conf.app_config)
    # 获取旧修订版
    old_revision = None
    if old_revision_id:
        old_revision = File.objects(id=old_revision_id, type=FileType.TEXT).first()
    # 获取file
    file = File.objects(id=file_id, type=FileType.TEXT).first()
    if file is None:
        return f"跳过，文件不存在，File <{file_id}>"
    # 如果文本是成功或解析中状态则跳过
    if file.parse_status == ParseStatus.PARSE_SUCCEEDED:
        return f"跳过，文件已成功解析，File <{file_id}>"
    if file.parse_status == ParseStatus.PARSING:
        return f"跳过，文件解析中，File <{file_id}>"
    # 将所有File设置成处理中，并设置开始时间
    file.update(
        parse_status=ParseStatus.PARSING, parse_start_time=datetime.datetime.utcnow(),
    )
    # 下载文件，并获取内容
    text_file = oss.download(oss_file_prefix, file.save_name)
    try:
        text = text_file.read()
    except Exception as e:
        file.update(
            parse_status=ParseStatus.PARSE_FAILED,
            inc__parse_times=1,
            parse_error_type=ParseErrorType.FILE_CAN_NOT_READ,
        )
        logger.error(e)
        return f"失败：文件损坏 (File<{file.id}>)"
        # 检测字符集
    text_charset = chardet.detect(text)["encoding"]
    try:
        text = text.decode(text_charset)
    except Exception as e:
        file.update(
            parse_status=ParseStatus.PARSE_FAILED,
            inc__parse_times=1,
            parse_error_type=ParseErrorType.TEXT_UNKNOWN_CHARSET,
        )
        logger.error(e)
        return f"失败：字符集转换失败 (File<{file.id}>)"
    lines = re.split(r"\n|\r\n|\r", text)
    # 为文件生成翻译原文
    for key, line in enumerate(lines):
        source = file.create_source(line, rank=key)
        # 如果为空内容，则不进行下步操作
        if source.blank:
            continue
        # 如果有旧修订版则将相同的翻译拷贝给新的
        if old_revision and old_revision != file:
            old_source = old_revision.sources().filter(content=line).first()
            # 如果有旧的一模一样的原文
            if old_source:
                source.copy(old_source)
        # 寻找术语并添加
        source.find_terms()
    # 将File设置成处理成功，并清理task_id/开始时间/解析次数
    file.update(
        parse_status=ParseStatus.PARSE_SUCCEEDED,
        unset__parse_times=1,
        unset__parse_task_id=1,
        unset__parse_start_time=1,
    )
    return f"成功：File<{file_id}>"


def parse_text(file_id, /, *, old_revision_id=None, run_sync=False):
    if run_sync:
        # 同步执行
        parse_text_task(file_id, old_revision_id)
        return SyncResult()
    else:
        # 异步执行
        return parse_text_task.delay(file_id, old_revision_id)


@celery.task(name="tasks.safe_task", bind=True, max_retries=3)
def safe_task(self, file_id):
    """发送安全检测请求"""
    from app.models.file import File
    from app.models.project import Project
    from app.models.team import Team

    (Project, Team)
    # 配置文件
    green_client = client.AcsClient(
        celery.conf.app_config["SAFE_ACCESS_KEY_ID"],
        celery.conf.app_config["SAFE_ACCESS_KEY_SECRET"],
        "cn-shanghai",
    )
    region_provider.modify_point(
        "Green", "cn-shanghai", "green.cn-shanghai.aliyuncs.com"
    )
    oss_file_prefix = celery.conf.app_config["OSS_FILE_PREFIX"]
    connect_db(celery.conf.app_config)
    oss.init(celery.conf.app_config)
    # 获取file
    file = File.objects(id=file_id, type=FileType.IMAGE).first()
    if file is None:
        return f"跳过，文件不存在，File <{file_id}>"
    # 如果图片是成功或等待结果状态则跳过
    if file.safe_status in [
        FileSafeStatus.NEED_HUMAN_CHECK,
        FileSafeStatus.SAFE,
        FileSafeStatus.BLOCK,
    ]:
        return "跳过，文件已有检测结果，File <{file_id}>"
    if file.safe_status == FileSafeStatus.WAIT_RESULT:
        # 报告开始时间
        start_time = "无"
        if file.safe_start_time:
            start_time = str(file.safe_start_time)
        return f"跳过，文件正在等待结果，开始时间：{start_time}，File <{file_id}>"

    # 通过sdk建立请求头
    request = RoaRequest("Green", "2017-08-25", "ImageAsyncScan", "green")
    request.set_uri_pattern("/green/image/asyncscan")
    request.set_method("POST")
    request.set_accept_format("JSON")
    # 异步支持多张图片，最多50张
    tasks = [
        {
            "dataId": str(uuid.uuid1()),
            "url": oss.sign_url(oss_file_prefix, file.save_name),
            "time": datetime.datetime.utcnow().microsecond,
        }
    ]
    request.set_content(json.dumps({"tasks": tasks, "scenes": ["porn"]}))
    try:
        response = green_client.do_action_with_exception(request)
        data = json.loads(response)
        if data["code"] == 200:
            task_id = data["data"][0]["taskId"]
            # 建立获取结果任务
            result = safe_result_task.apply_async(args=(file_id,), countdown=120)
            # 将File设置成处理中，并设置开始时间
            file.update(
                safe_status=FileSafeStatus.WAIT_RESULT,
                safe_result_id=task_id,
                safe_start_time=datetime.datetime.utcnow(),
                safe_task_id=result.task_id,
            )
            return "成功：稍后查询结果"
        else:
            raise Exception(f"阿里云绿网code非200：{data}")
    except Exception as e:
        # 尝试重新访问
        try:
            self.retry(countdown=5)
            file.update(safe_status=FileSafeStatus.QUEUING)
            return f"失败：重试，错误内容：({e})"
        except MaxRetriesExceededError:
            file.update(
                safe_status=FileSafeStatus.NEED_MACHINE_CHECK,
                unset__safe_result_id=1,
                unset__safe_start_time=1,
            )
            return f"失败：超过最大重试次数，错误内容：({e})"


def safe(file_id):
    return safe_task.delay(file_id)


@celery.task(name="tasks.safe_result_task", bind=True, max_retries=10)
def safe_result_task(self, file_id):
    """获取检测安全检测结果"""
    from app.models.file import File
    from app.models.project import Project
    from app.models.team import Team

    (Project, Team)
    # 配置
    green_client = client.AcsClient(
        celery.conf.app_config["SAFE_ACCESS_KEY_ID"],
        celery.conf.app_config["SAFE_ACCESS_KEY_SECRET"],
        "cn-shanghai",
    )
    region_provider.modify_point(
        "Green", "cn-shanghai", "green.cn-shanghai.aliyuncs.com"
    )
    oss_file_prefix = celery.conf.app_config["OSS_FILE_PREFIX"]
    connect_db(celery.conf.app_config)
    oss.init(celery.conf.app_config)
    # 获取file
    file = File.objects(id=file_id, type=FileType.IMAGE).first()
    if file is None:
        return f"跳过：文件不存在，File <{file_id}>"
    # 如果图片是成功或等待结果状态则跳过
    if file.safe_status != FileSafeStatus.WAIT_RESULT:
        return f"跳过：文件状态不是WAIT_RESULT，File <{file_id}>"
    # 配置请求
    request = RoaRequest("Green", "2017-08-25", "ImageAsyncScanResults", "green")
    request.set_uri_pattern("/green/image/results")
    request.set_method("POST")
    request.set_accept_format("JSON")
    request.set_content(json.dumps([file.safe_result_id]))
    try:
        response = green_client.do_action_with_exception(request)
        result = json.loads(response)
        if result["code"] == 200:
            task_results = result["data"]
            for task_result in task_results:
                if task_result["code"] == 200:
                    scene_results = task_result["results"]
                    for scene_result in scene_results:
                        scene = scene_result["scene"]
                        suggestion = scene_result["suggestion"]
                        if scene == "porn":
                            # 图片正常设置为安全
                            if suggestion == "pass":
                                file.update(
                                    safe_status=FileSafeStatus.SAFE,
                                    unset__safe_result_id=1,
                                    unset__safe_start_time=1,
                                    unset__safe_task_id=1,
                                )
                            # 确认黄图直接屏蔽
                            elif suggestion == "block":
                                # 删除oss上文件
                                oss.delete(oss_file_prefix, file.save_name)
                                file.update(
                                    save_name="",
                                    file_not_exist_reason=FileNotExistReason.BLOCK,  # noqa: E501
                                    safe_status=FileSafeStatus.BLOCK,
                                    unset__safe_result_id=1,
                                    unset__safe_start_time=1,
                                    unset__safe_task_id=1,
                                )
                                file.inc_cache("file_size", -file.file_size)
                            # 需要人工审核 scene == 'review' 或其他
                            else:
                                file.update(
                                    safe_status=FileSafeStatus.NEED_HUMAN_CHECK,  # noqa: E501
                                    unset__safe_result_id=1,
                                    unset__safe_start_time=1,
                                    unset__safe_task_id=1,
                                )
                    return f"成功：Image <{file_id}>，详细内容：{task_results}"
                else:
                    raise Exception(f"阿里云绿网内task数组code非200：{result}")
        else:
            raise Exception(f"阿里云绿网code非200：{result}")
    except Exception as e:
        logger.error(e)
        # 尝试重新访问
        try:
            self.retry(countdown=30)
            return f"失败：重试，错误内容：{e}"
        except MaxRetriesExceededError:
            file.update(
                safe_status=FileSafeStatus.NEED_MACHINE_CHECK,
                unset__safe_result_id=1,
                unset__safe_start_time=1,
                unset__safe_task_id=1,
            )
            return f"失败：超过最大尝试次数，错误内容：{e}"


@celery.task(name="tasks.find_terms_task", time_limit=1200)
def find_terms_task(file_id):
    """
    为文件的source寻找术语

    :param file_id: 传入File的Id(str or ObjectId)
    :return:
    """
    from app.models.file import File
    from app.models.project import Project
    from app.models.team import Team
    from app.models.term import Term
    from app.models.user import User

    (Project, Team, Term, User)
    # 配置
    connect_db(celery.conf.app_config)
    # 获取file
    file = File.objects(id=file_id, type=FileType.TEXT).first()
    if file is None:
        return f"跳过：文件不存在，File <{file_id}>"
    # 如果术语寻找中则跳过
    if file.find_terms_status == FindTermsStatus.FINDING:
        return f"跳过：文件寻找术语中，File <{file_id}>"
    # 将所有File设置成寻找术语中，并设置开始时间
    file.update(
        find_terms_status=FindTermsStatus.FINDING,
        find_terms_start_time=datetime.datetime.utcnow(),
    )
    for source in file.sources()():
        source.find_terms()
    # 将File设置成处理成功，并清理task_id/开始时间/解析次数
    file.update(
        find_terms_status=FindTermsStatus.FINISHED,
        unset__find_terms_task_id=1,
        unset__find_terms_start_time=1,
    )
    return f"成功：File<{file_id}>"


def find_terms(file_id, /, *, run_sync=False):
    if run_sync:
        # 同步执行
        find_terms_task(file_id)
        return SyncResult()
    else:
        # 异步执行
        return find_terms_task.delay(file_id)
