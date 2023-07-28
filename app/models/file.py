from typing import NoReturn, Union
import datetime
import math
import re
import mongoengine
from bson import ObjectId
from flask import current_app
from flask_babel import gettext
from mongoengine import (
    CASCADE,
    NULLIFY,
    PULL,
    BooleanField,
    DateTimeField,
    Document,
    FloatField,
    IntField,
    ListField,
    LongField,
    ReferenceField,
    StringField,
)

from app import oss
from app.constants.storage import StorageType
from app.core.responses import MoePagination
from app.decorators.file import need_activated, only, only_file
from app.exceptions import (
    FileIsActivatedError,
    FilenameDuplicateError,
    FilenameIllegalError,
    FileNotExistError,
    FileParentIsSameError,
    FileParentIsSelfError,
    FileParentIsSubFolderError,
    FileTypeNotSupportError,
    FolderNotExistError,
    FolderNoVersionError,
    SourceFileNotExist,
    SourceMovingError,
    SourceNotExistError,
    SuffixNotInFileTypeError,
    TargetIsNotFolderError,
    TipEmptyError,
    TranslationNotUniqueError,
)
from app.models.target import Target
from app.models.term import Term
from app.tasks.file_parse import parse_text, safe
from app.tasks.ocr import ocr
from app.constants.source import SourcePositionType
from app.constants.file import (
    FileNotExistReason,
    FileSafeStatus,
    FileType,
    FindTermsStatus,
    ImageOCRPercent,
    ImageParseStatus,
    ParseErrorType,
    ParseStatus,
)
from app.tasks.thumbnail import create_thumbnail
from app.utils import default
from app.utils.file import get_file_size
from app.utils.hash import get_file_md5
from app.utils.logging import logger
from app.utils.mongo import mongo_order, mongo_slice
from app.utils.type import is_number

default_translations_order = ["-selected", "-proofread_content", "-edit_time"]


class Filename:
    """文件名类，用于检查文件名合法性，及生成用于排序的文件名"""

    def __init__(self, name, folder=False):
        self.name = name
        # 检查文件名有效性
        self._check_valid()
        # 获取前后缀，文件夹则没有后缀，prefix即name
        if folder:
            self.prefix, self.suffix = name, ""
            self.file_type = FileType.FOLDER
        else:
            self.prefix, self.suffix = self._get_prefix_and_suffix()
            self.file_type = FileType.by_suffix(self.suffix)
        # 获得排序用名称
        self.sort_name = self._get_sort_name(6)

    def _check_valid(self):
        """检测文件名是否合法"""
        # 文件名不能为空
        if self.name.replace(" ", "") == "":
            raise FilenameIllegalError(gettext("文件名为空"))
        # 文件名过长
        if len(self.name) > 127:
            raise FilenameIllegalError(gettext("文件名过长"))
        # 文件名不能是 . 或 ..
        if self.name.replace(" ", "") == "." or self.name.replace(" ", "") == "..":
            raise FilenameIllegalError(gettext("文件名不能是 . 或 .."))
        # 文件名不能以 . 结尾
        if self.name.replace(" ", "").endswith("."):
            raise FilenameIllegalError(gettext("文件名不能以 . 结尾"))
        # 文件名前缀为空
        if self.name.rsplit(".", 1)[0].replace(" ", "") == "":
            raise FilenameIllegalError(gettext("文件名前缀为空"))
        # 检测名称内是否有非法字符
        # \ / : * ? " < > |
        invalid_chars = {
            "\u005c",
            "\u002f",
            "\u003a",
            "\u002a",
            "\u003f",
            "\u0022",
            "\u003c",
            "\u003e",
            "\u007c",
        }
        if len(invalid_chars & set(self.name)):
            raise FilenameIllegalError(gettext(r'文件名不能包含下列任何字符: \ / : * ? " < > |'))

    def _get_prefix_and_suffix(self):
        """获取前后缀"""
        prefix_and_suffix = self.name.rsplit(".", 1)
        if len(prefix_and_suffix) == 1:
            prefix = prefix_and_suffix[0]
            suffix = ""
        else:
            prefix = prefix_and_suffix[0]
            suffix = prefix_and_suffix[1]
        return prefix, suffix

    def _get_sort_name(self, width):
        """返回用于排序的名称，使用前缀排序，将前缀中数字补足一定位数用于排序"""
        # 将前缀中数字与其他字符拆成列表
        # 形如 ['book', '1', '-', '002', '.jpg']
        name_parts = re.findall(r"\d+|\D+", self.prefix)
        sort_name = ""
        for part in name_parts:
            # 是数字则补零在前面
            if is_number(part):
                sort_name += "0" * (width - len(part)) + part
            else:
                sort_name += part
        return sort_name


class File(Document):
    """文件"""

    # == 基本信息 ==
    name = StringField(db_field="n", required=True)  # 文件名
    type = IntField(db_field="t", required=True)  # 文件类型

    # == 归属 ==
    project = ReferenceField("Project", db_field="p", required=True)  # 所属项目
    parent = ReferenceField("File", db_field="f")  # 父级文件夹
    ancestors = ListField(ReferenceField("File"), db_field="a", default=list)  # 祖先文件夹

    # == 排序 ==
    sort_name = StringField(db_field="sn", required=True)  # 用于排序的文件名
    dir_sort_name = StringField(db_field="dn", required=True, default="")  # 用于排序的路径名

    # == 源文件相关 ==
    save_name = StringField(db_field="sa", default="")  # 上传的文件名
    md5 = StringField(db_field="md", default="")  # md5

    # 文件大小，单位KB，需要使用inc_cache更新
    file_size = LongField(db_field="fs", default=0)
    file_not_exist_reason = IntField(
        db_field="fn", default=FileNotExistReason.UNKNOWN
    )  # 源文件不存在的原因

    # 缓存，需要使用inc_cache/update_cache更新
    folder_count = IntField(db_field="fo", default=0)  # 文件夹数量
    file_count = IntField(db_field="fc", default=0)  # 文件数量
    source_count = IntField(db_field="sc", default=0)  # 原文数量
    translated_source_count = IntField(db_field="tsc", default=0)  # 已翻译的原文数量
    checked_source_count = IntField(db_field="csc", default=0)  # 已审核的原文数量
    edit_time = DateTimeField(db_field="et", default=datetime.datetime.utcnow)  # 修改时间

    # == 修订版相关 ==
    # 上一个修订版，仅用于解析时从上一个修订版获取翻译
    old_revision = ReferenceField("File", db_field="ov", reverse_delete_rule=NULLIFY)
    revision = IntField(db_field="v", required=True, default=1)  # 修订版号
    activated = BooleanField(db_field="ac", required=True, default=True)  # 激活的修订版

    # == 安全（涉政涉黄）检测数据 ==
    safe_status = IntField(
        db_field="ss", default=FileSafeStatus.NEED_MACHINE_CHECK
    )  # 任务状态
    safe_task_id = StringField(db_field="sti")  # 文件安全检测任务celery id，用于查询状态
    safe_result_id = StringField(db_field="sri")  # 文件安全检测任务id，用于向阿里云查询结果
    safe_start_time = DateTimeField(db_field="sst")  # 文件安全检测开始时间

    # == 解析原文 ==
    parse_status = IntField(db_field="ps", default=ParseStatus.NOT_START)  # 是否完成文件解析
    # ocr/解析的次数，用于多次请求ocr、解析不成功暂时屏蔽
    parse_times = IntField(db_field="pt", default=0)
    parse_task_id = StringField(db_field="pti")  # ocr/解析的任务celery id，用于查询状态
    parse_start_time = DateTimeField(db_field="pst")  # ocr/解析开始时间
    parse_error_type = IntField(db_field="pe")  # 错误详情
    image_ocr_percent = IntField(db_field="op", default=0)  # OCR 进度

    # == 寻找术语 ==
    find_terms_status = IntField(
        db_field="ft", default=FindTermsStatus.QUEUING
    )  # 寻找术语的状态
    find_terms_task_id = StringField(db_field="ftt")  # 寻找术语的任务celery id，用于查询状态
    find_terms_start_time = DateTimeField(db_field="fts")  # 寻找术语开始时间

    # == 锁 ==
    source_moving = BooleanField(db_field="sm", default=False)  # 原文的rank是否正在修改

    meta = {
        "indexes": [
            ("activated", "name", "parent", "project"),
            ("type", "sort_name"),
            ("type", "-sort_name"),
            ("dir_sort_name", "type", "sort_name"),
            ("dir_sort_name", "type", "-sort_name"),
        ]
    }

    def clean(self):
        if self.parent:
            # 确认父级必须属于同项目
            if self.parent.project != self.project:
                raise FolderNotExistError
            # 确认父级必须是文件夹
            if self.parent.type != FileType.FOLDER:
                raise TargetIsNotFolderError
        # 处理dir_sort_name和ancestors
        if self.parent:
            self.ancestors = self.parent.ancestors + [self.parent]
            self.dir_sort_name = self.parent.dir_sort_name + self.parent.sort_name + "/"

    @classmethod
    def by_id(cls, id):
        file = cls.objects(id=id).first()
        if file is None:
            raise FileNotExistError
        return file

    @property
    def revisions(self):
        """获得同名的所有修订版，包括本修订版"""
        return self.project.get_files(
            name=self.name, parent=self.parent, activated="all"
        )

    @property
    def activated_revision(self):
        """获得同名的激活的修订版"""
        return self.project.get_files(
            name=self.name, parent=self.parent, activated=True
        ).first()

    @property
    def deactivated_revisions(self):
        """获得同名的未激活的修订版"""
        return self.project.get_files(
            name=self.name, parent=self.parent, activated=False
        )

    @property
    def ancestor_ids(self):
        """返回祖先的ids，是一个包含ObjectId的列表"""
        son = self.to_mongo(use_db_field=False, fields=["ancestors"])
        ids = son.get("ancestors", [])
        return ids

    def ancestor_caches(self, target):
        """返回祖先的FileTargetCache"""
        caches = FileTargetCache.objects(file__in=self.ancestor_ids, target=target)
        return caches

    def cache(self, target):
        """返回自己的FileTargetCache"""
        cache = FileTargetCache.objects(file=self, target=target).first()
        return cache

    @need_activated
    def create_revision(self):
        """创建一个修订版"""
        file = File(
            name=self.name,
            project=self.project,
            parent=self.parent,
            type=self.type,
            sort_name=self.sort_name,
            activated=False,
            old_revision=self,
            revision=self.revisions.count() + 1,
        ).save()
        # 创建FileTargetCache
        for target in self.project.targets():
            file.create_target_cache(target)
        return file

    def activate_revision(self):
        """激活当前修订版"""
        # 文件夹不允许有修订版
        if self.type == FileType.FOLDER:
            raise FolderNoVersionError
        # 已激活
        if self.activated:
            raise FileIsActivatedError
        # 切换激活的修订版
        old_activated_revision = self.activated_revision
        old_activated_revision.update(activated=False)
        self.update(activated=True)
        self.reload()  # 刷新activated状态后，才能使用inc_cache，并且更新self的各种缓存，以免计数错误
        # 更新父目标缓存
        self.inc_cache(
            "source_count",
            self.source_count - old_activated_revision.source_count,
            update_self=False,
        )
        self.inc_cache(
            "file_size",
            self.file_size - old_activated_revision.file_size,
            update_self=False,
        )
        self.update_cache("edit_time", datetime.datetime.utcnow())
        # 更新项目翻译计数缓存
        for target in self.project.targets():
            self.inc_cache(
                "translated_source_count",
                (
                    self.cache(target=target).translated_source_count
                    - old_activated_revision.cache(
                        target=target
                    ).translated_source_count
                ),
                update_self=False,
                target=target,
            )
            self.inc_cache(
                "checked_source_count",
                (
                    self.cache(target=target).checked_source_count
                    - old_activated_revision.cache(target=target).checked_source_count
                ),
                update_self=False,
                target=target,
            )

    @need_activated
    def rename(self, name):
        """重命名"""
        # 检查是否有同名文件
        old_file = self.project.get_files(name=name, parent=self.parent).first()
        # 如果有同名文件
        if old_file:
            # 不是自身，文件名重复，抛出异常
            if old_file != self:
                raise FilenameDuplicateError
            # 是自身，文件名一模一样，直接跳出
            if old_file.name == name:
                return
        # 是否是文件夹
        is_folder = bool(self.type == FileType.FOLDER)
        # 验证新名称合法性
        filename = Filename(name, folder=is_folder)
        # 新后缀文件类型必须与原类型相同
        if filename.file_type != self.type:
            raise SuffixNotInFileTypeError
        # 用于替换的dir_sort_name
        old_dir_sort_name = self.dir_sort_name + self.sort_name
        dir_sort_name = self.dir_sort_name + filename.sort_name
        # 修改名称
        self.name = filename.name
        # 修改排序名称
        self.sort_name = filename.sort_name
        self.save()
        # 文件夹还要替换所有子文件/子文件夹的目录排序名
        # TODO: 此部分需要完善测试！应该可以使用pymongo的bulk_write优化性能
        if self.type == FileType.FOLDER:
            files = File.objects(ancestors=self)
            for file in files:
                file.dir_sort_name = (
                    dir_sort_name + file.dir_sort_name[len(old_dir_sort_name) :]
                )
                file.save()

    @need_activated
    def move_to(self, parent):
        """将某个文件或文件夹移动到另一个地方"""
        # 强制从数据库更新自身，以免之前有删除、建立文件夹操作，影响最后的计数缓存
        self.reload()
        if parent is not None:
            parent = self.project.get_folder(parent)
            # 目标文件夹不能是自己本身
            if self == parent:
                raise FileParentIsSelfError
            # 不能移动到自己的子文件夹
            if File.objects(id=parent.id, ancestors=self).count() > 0:
                raise FileParentIsSubFolderError
        # 目标文件夹与原父级文件夹相同
        if self.parent == parent:
            raise FileParentIsSameError
        # 检查是否有同名文件
        old_file = self.project.get_files(name=self.name, parent=parent).first()
        if old_file:
            raise FilenameDuplicateError
        # 之前的祖先和目录排序名
        old_parent = self.parent
        old_ancestors = self.ancestors
        old_dir_sort_name = self.dir_sort_name
        # 新的祖先和目录排序名
        if parent:
            dir_sort_name = parent.dir_sort_name + parent.sort_name + "/"
            ancestors = parent.ancestors + [parent]
        else:
            dir_sort_name = ""
            ancestors = []
        # 修改自己的父级，祖先列表和目录排序名
        self.update(parent=parent, ancestors=ancestors, dir_sort_name=dir_sort_name)
        # 修改未激活修订版的父级，祖先列表和目录排序名
        self.deactivated_revisions.update(
            parent=parent, ancestors=ancestors, dir_sort_name=dir_sort_name
        )
        # 文件夹还要替换所有子文件/子文件夹的祖先列表和目录排序名
        if self.type == FileType.FOLDER:
            files = File.objects(ancestors=self)
            # 替换祖先列表
            files.update(pull_all__ancestors=old_ancestors)  # 从列表中删除原来的祖先
            files.update(push__ancestors__0=ancestors)  # 拼接上新的的祖先
            # 替换目录排序名
            # TODO: 此部分需要完善测试！应该可以使用pymongo的bulk_write优化性能
            files = File.objects(ancestors=self)
            for file in files:
                file.dir_sort_name = (
                    dir_sort_name + file.dir_sort_name[len(old_dir_sort_name) :]
                )
                file.save()
        # 更新计数缓存
        if parent:
            if self.type == FileType.FOLDER:
                parent.inc_cache("file_count", self.file_count, update_project=False)
                parent.inc_cache(
                    "folder_count", self.folder_count + 1, update_project=False
                )
            else:
                parent.inc_cache("file_count", 1, update_project=False)
            parent.inc_cache("source_count", self.source_count, update_project=False)
            parent.inc_cache("file_size", self.file_size, update_project=False)
            # 更新翻译缓存
            for target in self.project.targets():
                parent.inc_cache(
                    "translated_source_count",
                    self.cache(target=target).translated_source_count,
                    update_project=False,
                    target=target,
                )
                parent.inc_cache(
                    "checked_source_count",
                    self.cache(target=target).checked_source_count,
                    update_project=False,
                    target=target,
                )
        if old_parent:
            if self.type == FileType.FOLDER:
                old_parent.inc_cache(
                    "file_count", -self.file_count, update_project=False
                )
                old_parent.inc_cache(
                    "folder_count",
                    -(self.folder_count + 1),
                    update_project=False,
                )
            else:
                old_parent.inc_cache("file_count", -1, update_project=False)
            old_parent.inc_cache(
                "source_count", -self.source_count, update_project=False
            )
            old_parent.inc_cache("file_size", -self.file_size, update_project=False)
            # 更新翻译缓存
            for target in self.project.targets():
                old_parent.inc_cache(
                    "translated_source_count",
                    -self.cache(target=target).translated_source_count,
                    update_project=False,
                    target=target,
                )
                old_parent.inc_cache(
                    "checked_source_count",
                    -self.cache(target=target).checked_source_count,
                    update_project=False,
                    target=target,
                )

    def create_target_cache(self, target):
        # 已有缓存则不创建
        old_cache = FileTargetCache.objects(file=self, target=target).first()
        if old_cache:
            return old_cache
        return FileTargetCache(file=self, target=target).save()

    @need_activated
    def inc_cache(
        self,
        cache_name: "str",
        step: int,
        update_self: bool = True,
        update_project: bool = True,
        target: Target = None,
    ):
        """增加某个字段的计数缓存，并且向上级文件夹映射"""
        # 0则不请求数据库
        if step == 0:
            return
        # 翻译缓存
        if cache_name in ["translated_source_count", "checked_source_count"]:
            if target is None:
                raise ValueError("更新翻译缓存数据必须指定target")
            # 更新自身/父级缓存
            if update_self:
                FileTargetCache.objects(
                    file__in=[*self.ancestor_ids, self.id], target=target
                ).update(**{"inc__" + cache_name: step})
                File.objects(id__in=[*self.ancestor_ids, self.id]).update(
                    **{"inc__" + cache_name: step}
                )
            else:
                FileTargetCache.objects(
                    file__in=self.ancestor_ids, target=target
                ).update(**{"inc__" + cache_name: step})
                File.objects(id__in=self.ancestor_ids).update(
                    **{"inc__" + cache_name: step}
                )
            if update_project:
                self.project.inc_cache(cache_name, step, target=target)
        # 其他缓存
        else:
            # 没有此属性跳过
            if not hasattr(self, cache_name):
                return
            # 更新自身/父级缓存
            if update_self:
                File.objects(id__in=[*self.ancestor_ids, self.id]).update(
                    **{"inc__" + cache_name: step}
                )
            else:
                File.objects(id__in=self.ancestor_ids).update(
                    **{"inc__" + cache_name: step}
                )
            # 更新项目缓存
            if update_project:
                self.project.inc_cache(cache_name, step)

    @need_activated
    def update_cache(self, cache_name, value, update_self=True, update_project=True):
        """更新某个缓存字段"""
        # 没有此属性跳过
        if not hasattr(self, cache_name):
            return
        # 更新自身/父级缓存
        if update_self:
            File.objects(id__in=[*self.ancestor_ids, self.id]).update(
                **{cache_name: value}
            )
        else:
            File.objects(id__in=self.ancestor_ids).update(**{cache_name: value})
        # 更新项目缓存
        if update_project:
            self.project.update_cache(cache_name, value)

    @property
    def url(self):
        if not self.save_name:
            return ""
        return oss.sign_url(current_app.config["OSS_FILE_PREFIX"], self.save_name)

    @property
    def cover_url(self):
        if not self.save_name:
            return ""
        if current_app.config[
            "STORAGE_TYPE"
        ] == StorageType.LOCAL_STORAGE and not oss.is_exist(
            current_app.config["OSS_FILE_PREFIX"],
            self.save_name,
            process_name=current_app.config["OSS_PROCESS_COVER_NAME"],
        ):
            return "generating"
        return oss.sign_url(
            current_app.config["OSS_FILE_PREFIX"],
            self.save_name,
            process_name=current_app.config["OSS_PROCESS_COVER_NAME"],
        )

    @property
    def safe_check_url(self):
        if not self.save_name:
            return ""
        if current_app.config[
            "STORAGE_TYPE"
        ] == StorageType.LOCAL_STORAGE and not oss.is_exist(
            current_app.config["OSS_FILE_PREFIX"],
            self.save_name,
            process_name=current_app.config["OSS_PROCESS_SAFE_CHECK_NAME"],
        ):
            return "generating"
        return oss.sign_url(
            current_app.config["OSS_FILE_PREFIX"],
            self.save_name,
            process_name=current_app.config["OSS_PROCESS_SAFE_CHECK_NAME"],
        )

    @only_file
    def has_real_file(self):
        return bool(self.save_name)

    @only_file
    def download_real_file(self, local_path=None):
        """下载源文件"""
        # 从oss获取源文件
        if not self.save_name:
            raise SourceFileNotExist(self.file_not_exist_reason)
        return oss.download(
            current_app.config["OSS_FILE_PREFIX"], self.save_name, local_path=local_path
        )

    @only_file
    def upload_real_file(self, real_file, do_safe_scan=False):
        """
        上传源文件
        """
        # 尝试删除源文件
        self.delete_real_file()
        # 重置安全检测数据
        self.update(
            safe_status=FileSafeStatus.NEED_MACHINE_CHECK,
            unset__safe_task_id=1,
            unset__safe_result_id=1,
            unset__safe_start_time=1,
        )
        # 生成用于保存的名称
        filename = Filename(self.name)
        save_name = str(ObjectId()) + "." + filename.suffix
        # 文件md5
        md5 = get_file_md5(real_file)
        # 文件大小
        file_size = math.ceil(get_file_size(real_file))  # 获取文件大小，去掉小数
        # 将文件上传到OSS
        oss_result = oss.upload(
            current_app.config["OSS_FILE_PREFIX"], save_name, real_file
        )
        # 替换原存储名和md5
        self.update(save_name=save_name, md5=md5)
        # 更新文件大小，非激活修订版只更新自身文件大小
        if self.activated:
            self.inc_cache("file_size", file_size - self.file_size)
        else:
            self.update(file_size=file_size)
        # 更新修改时间
        self.update_cache("edit_time", datetime.datetime.utcnow())
        # 检查文件安全性
        if do_safe_scan:
            self.safe_scan()
        # 文本自动解析生成 Source
        if self.type == FileType.TEXT:
            self.parse()
        if (
            self.type == FileType.IMAGE
            and current_app.config["STORAGE_TYPE"] == StorageType.LOCAL_STORAGE
        ):
            create_thumbnail(str(self.id))
        self.reload()
        return oss_result

    @only_file
    def delete_real_file(
        self,
        init_obj=True,
        update_cache=True,
        file_not_exist_reason=FileNotExistReason.UNKNOWN,
    ):
        """
        删除源文件

        :param init_obj: 重置对象
        :param update_cache: 重置对象时，是否更新缓存数据
        :param file_not_exist_reason: 删除原因
        :return:
        """
        # 如果是文件夹则跳过
        if self.has_real_file:
            # 物理删除源文件
            oss_result = oss.delete(
                current_app.config["OSS_FILE_PREFIX"],
                [
                    self.save_name,
                    current_app.config["OSS_PROCESS_COVER_NAME"] + "-" + self.save_name,
                    current_app.config["OSS_PROCESS_SAFE_CHECK_NAME"]
                    + "-"
                    + self.save_name,
                ],
            )
            # 初始化对象，并更新缓存计数
            if init_obj:
                self.update(
                    save_name="",
                    md5="",
                    file_not_exist_reason=file_not_exist_reason,
                )
                # 更新缓存数据
                if update_cache:
                    # 非激活修订版只更新自身文件大小
                    if self.activated:
                        self.inc_cache("file_size", -self.file_size)
                    else:
                        self.update(file_size=0)
                    self.update_cache("edit_time", datetime.datetime.utcnow())
                self.reload()
            return oss_result

    @only_file
    def _draw(self):
        """[用于测试]画出图片中的原文"""
        import requests
        from PIL import Image, ImageDraw
        from io import BytesIO

        # 从网络中打开图片
        response = requests.get(self.url)
        im = Image.open(BytesIO(response.content))
        for source in self.sources():
            draw = ImageDraw.Draw(im)
            point_half_width = 2
            draw.polygon(
                [
                    (
                        source.x * im.width - point_half_width,
                        source.y * im.height - point_half_width,
                    ),
                    (
                        source.x * im.width + point_half_width,
                        source.y * im.height - point_half_width,
                    ),
                    (
                        source.x * im.width + point_half_width,
                        source.y * im.height + point_half_width,
                    ),
                    (
                        source.x * im.width - point_half_width,
                        source.y * im.height + point_half_width,
                    ),
                ],
                "red",
            )
            # draw.polygon([(v[0] * im.width, v[1] * im.height)
            # for v in source.vertices], fill=(200, 10, 10, 128),
            #              outline=(200, 10, 10, 255))
        # 显示图片
        im.show()

    @need_activated
    def clear(self):
        """
        删除源文件，并删除对象，更新计数缓存
        """
        # 强制从数据库更新自身，以免之前有删除、建立文件夹操作，影响最后的计数缓存
        self.reload()
        # 如果是文件夹，还需要物理删除所有下级文件
        if self.type == FileType.FOLDER:
            # 包含所有下级的文件夹、文件、修订版
            files = File.objects(ancestors=self)
            # 物理删除源文件
            for file in files:
                if file.type != FileType.FOLDER:
                    file.delete_real_file(init_obj=False)
            files.delete()
        # 如果是文件，需要物理删除文件，以及相关修订版文件
        else:
            # 相关未激活的修订版
            deactivated_revisions = self.deactivated_revisions
            # 物理删除源文件
            for revision in self.deactivated_revisions:
                revision.delete_real_file(init_obj=False)
            deactivated_revisions.delete()
            # 物理删除自己的源文件
            self.delete_real_file(init_obj=False)
        # 更新计数缓存
        self.inc_cache("file_size", -self.file_size, update_self=False)
        if self.type == FileType.FOLDER:
            self.inc_cache("folder_count", -(self.folder_count + 1), update_self=False)
            self.inc_cache("file_count", -self.file_count, update_self=False)
        else:
            self.inc_cache("file_count", -1, update_self=False)
        # 更新翻译计数缓存
        for target in self.project.targets():
            self.inc_cache(
                "translated_source_count",
                -self.cache(target=target).translated_source_count,
                update_self=False,
                target=target,
            )
            self.inc_cache(
                "checked_source_count",
                -self.cache(target=target).checked_source_count,
                update_self=False,
                target=target,
            )
        self.inc_cache("source_count", -self.source_count)
        # 更新修改时间
        self.update_cache("edit_time", datetime.datetime.utcnow())
        # 删除自身
        self.delete()

    def to_json_file(self):
        """
        [不同类型分别处理]
        获取译文
        """
        # 所有图片文件的翻译会合并到一个文件

        # 文本的翻译会单独列出

    @only_file
    def safe_scan(self):
        """
        [不同类型分别处理]
        文件安全检测
        """
        # 测试不进行文件安全检测
        if current_app.config.get("TESTING", False):
            return
        if self.type == FileType.IMAGE:
            # 将解析/图片鉴黄设置成排队中
            self.update(safe_status=FileSafeStatus.QUEUING)
            # 调用OCR解析图片中的文字，并生成原文
            result = safe(str(self.id))
            # 记录task_id，用于之后查询进度
            self.update(safe_task_id=result.task_id)
        # 文本暂无安全检测
        elif self.type == FileType.TEXT:
            pass
        else:
            logger.warning(f"没有为FileType({self.type}),设置相应safe_scan处理方案")

    @only_file
    @need_activated
    def parse(self):
        """
        [不同类型分别处理]
        从文件中解析原文

        :return:
        """
        # 图片OCR解析
        if self.type == FileType.IMAGE:
            return "单个图片OCR暂未实现，ocr(type='file')"
            # 如果不是测试则异步执行
            run_sync = current_app.config.get("TESTING", False)
            # 将解析设置成排队中
            self.update(parse_status=ParseStatus.QUEUING)
            # 调用OCR解析图片中的文字，并生成原文
            result = ocr("file", str(self.id))
            # 记录task_id，用于之后查询进度
            self.update(parse_task_id=result.task_id)
        # 文本分行处理
        elif self.type == FileType.TEXT:
            # 清空原文
            self.clear_all_sources()
            # 如果不是测试则异步执行
            run_sync = current_app.config.get("TESTING", False)
            # 将解析设置成排队中
            self.update(parse_status=ParseStatus.QUEUING)
            # 获取旧版本 id
            if self.old_revision:
                old_revision_id = str(self.old_revision.id)
            else:
                old_revision_id = None
            # 解析TXT，并生成原文
            result = parse_text(
                str(self.id),
                old_revision_id=old_revision_id,
                run_sync=run_sync,
            )
            # 记录task_id，用于之后查询进度
            self.update(parse_task_id=result.task_id)
        else:
            logger.warning(f"没有为FileType({self.type}),设置相应parse处理方案")

    def next_source_rank(self):
        """返回下一个rank"""
        self.reload()
        # 获得 rank 最大的 source
        rank = 0
        lastestSource = self.sources(limit=1, order_by=["-rank"]).first()
        if lastestSource:
            rank = lastestSource.rank + 1
        return rank

    @need_activated
    def create_source(self, *args, **kwargs) -> Union["Source", NoReturn]:
        if self.type == FileType.TEXT:
            return self._create_text_source(*args, **kwargs)
        elif self.type == FileType.IMAGE:
            return self._create_image_source(*args, **kwargs)
        else:
            raise RuntimeError(f"没有为FileType({self.type}),设置相应create_source处理方案")

    @only(FileType.TEXT)
    @need_activated
    def _create_text_source(self, content, rank=None) -> "Source":
        """为文本增加原文，仅文本类型文件可用"""
        # 注意：如果没有给予rank，则需要查询总Source数，5倍耗时
        if rank is None:
            rank = self.next_source_rank()
        # 是空白字段，则添加blank标签
        if content.strip() == "":
            blank = True  # 空白不更新原文数量
        else:
            blank = False
            self.inc_cache("source_count", 1)  # 更新原文数量
        source = Source(file=self, content=content, rank=rank, blank=blank).save()
        return source

    @only(FileType.IMAGE)
    @need_activated
    def _create_image_source(
        self,
        content,
        x=0,
        y=0,
        machine=False,
        rank=None,
        vertices=None,
        position_type=SourcePositionType.IN,
    ) -> "Source":
        """为图片增加原文（标签），仅图片类型文件可用"""
        if vertices is None:
            vertices = []
        # 注意：如果没有给予rank，则需要查询总Source数，5倍耗时
        if rank is None:
            rank = self.next_source_rank()
        # 创建原文（标签）
        source = Source(
            file=self,
            x=x,
            y=y,
            content=content,
            rank=rank,
            machine=machine,
            vertices=vertices,
            position_type=position_type,
        ).save()
        self.inc_cache("source_count", 1)  # 更新原文数量
        return source

    @only_file
    @need_activated
    def clear_all_sources(self):
        """清空所有Source，并更新缓存"""
        self.sources().delete()
        for target in self.project.targets():
            self.inc_cache(
                "translated_source_count",
                -self.cache(target=target).translated_source_count,
                target=target,
            )
            self.inc_cache(
                "checked_source_count",
                -self.cache(target=target).checked_source_count,
                target=target,
            )
        self.inc_cache("source_count", -self.source_count)

    def sources(self, skip=None, limit=None, order_by: list = None):
        sources = Source.objects(file=self)
        # 排序处理
        sources = mongo_order(sources, order_by, ["rank"])
        # 分页处理
        sources = mongo_slice(sources, skip, limit)
        return sources

    @need_activated
    def to_translator(self, target, paging=True, show_blank=False, user=None):
        """
        返回图片翻译器所用的 json

        :param target: 翻译目标
        :param paging: 是否分页
        :param show_blank: 是否显示空行
        :return:
        """
        # 是否分页
        p = None
        if paging:
            p = MoePagination()
            sources = self.sources(skip=p.skip, limit=p.limit)
        else:
            sources = self.sources()
        # 仅显示不是空白的
        if not show_blank:
            sources = sources.filter(blank=False)
        data = [
            {
                **source.to_api(),
                "translations": [],
                "tips": [],
                "has_other_language_translation": False,
            }
            for source in sources
        ]
        # source_id：source_data的字典，用于快速向source插入翻译数据
        source_id_dict = {source["id"]: source for source in data}
        # ！插入翻译数据
        # 获取所有原文的自己的翻译
        my_translation_data = [
            t.to_api()
            for t in Translation.objects(user=user, source__in=sources, target=target)
        ]
        for td in my_translation_data:
            source = source_id_dict.get(td["source_id"])
            if source:
                source["my_translation"] = td
        # 取出所有原文的翻译数据（不包括自己的）
        translation_data = [
            t.to_api()
            for t in Translation.objects(
                user__ne=user, source__in=sources, target=target
            ).order_by(*default_translations_order)
        ]
        for td in translation_data:
            source = source_id_dict.get(td["source_id"])
            if source:
                source["translations"].append(td)
        # 检测其他语言是否有翻译
        other_language_translation_data = [
            t.to_api()
            for t in Translation.objects(source__in=sources, target__ne=target)
        ]
        for td in other_language_translation_data:
            source = source_id_dict.get(td["source_id"])
            if source:
                source["has_other_language_translation"] = True
        # ！插入tip数据
        # 一次取出所有tip数据
        tip_data = [
            t.to_api()
            for t in Tip.objects(source__in=sources, target=target).order_by(
                "-create_time"
            )
        ]
        for td in tip_data:
            source = source_id_dict.get(td["source_id"])
            if source:
                source["tips"].append(td)
        # 是否分页
        if p:
            return p.set_data(data, self.sources().count())
        else:
            return data

    def to_labelplus(self, /, *, target):
        """将翻译导出成labelplus格式"""
        data = ""
        if len(self.ancestors) > 0:
            path = "/".join([ancestors.name for ancestors in self.ancestors]) + "/"
        else:
            path = ""
        # 文件路径行
        data += ">>>>>>>>[" + path + self.name + "]<<<<<<<<\r\n"
        # 遍历所有原文
        for id, source in enumerate(self.sources(), start=1):
            group_id = source.position_type
            # 标签信息 ---[id]---[x,y,group_id]
            data += (
                "----------------["
                + str(id)
                + "]----------------["
                + str(source.x)
                + ","
                + str(source.y)
                + ","
                + str(group_id)
                + "]\r\n"
            )
            translation = source.best_translation(target=target)
            # 有翻译
            if translation:
                # 优先使用校对的内容
                if translation.proofread_content:
                    content = translation.proofread_content
                else:
                    content = translation.content
            else:
                content = ""
            # 统一使用 Windows 换行符
            content = content.replace("\n", "\r\n")
            # 再换行
            data += content + "\r\n"
        return data

    @need_activated
    def to_api(self):
        data = {
            "id": str(self.id),
            "name": self.name,
            "save_name": self.save_name,
            "type": self.type,
            "source_count": self.source_count,
            "translated_source_count": self.translated_source_count,
            "checked_source_count": self.checked_source_count,
            "file_not_exist_reason": self.file_not_exist_reason,
            "safe_status": self.safe_status,
            "parse_status": self.parse_status,
            "parse_error_type": self.parse_error_type,
            "parse_error_type_detail_name": ParseErrorType.get_detail_by_value(
                self.parse_error_type, "name"
            ),
            "parent_id": default(self.parent, attr_name="id", func=str),
        }
        if self.type == FileType.IMAGE:
            data["parse_status_detail_name"] = ImageParseStatus.get_detail_by_value(
                self.parse_status, "name"
            )
            data["url"] = self.url
            data["cover_url"] = self.cover_url
            data["safe_check_url"] = self.safe_check_url
            data["image_ocr_percent"] = self.image_ocr_percent
            data["image_ocr_percent_detail_name"] = ImageOCRPercent.get_detail_by_value(
                self.image_ocr_percent, "name"
            )
        else:
            data["parse_status_detail_name"] = ParseStatus.get_detail_by_value(
                self.parse_status, "name"
            )
        return data


class FileTargetCache(Document):
    """文件对于不同目标语言的计数缓存"""

    file = ReferenceField(
        "File", db_field="f", required=True, reverse_delete_rule=CASCADE
    )  # 所属文件
    target = ReferenceField(
        Target, db_field="t", required=True, reverse_delete_rule=CASCADE
    )
    translated_source_count = IntField(db_field="ts", default=0)  # 已翻译的原文数量
    checked_source_count = IntField(db_field="cs", default=0)  # 已校对的原文数量
    edit_time = DateTimeField(db_field="e", default=datetime.datetime.utcnow)

    meta = {
        "indexes": [
            ("file", "target"),
        ]
    }

    def to_api(self):
        data = {
            "id": str(self.id),
            "translated_source_count": self.translated_source_count,
            "checked_source_count": self.checked_source_count,
        }
        return data


class Source(Document):
    file = ReferenceField("File", db_field="f", reverse_delete_rule=CASCADE)
    rank = IntField(db_field="r", required=True)  # 排序
    content = StringField(db_field="c", default="")  # 内容
    # === 图片独有的参数 ===
    x = FloatField(db_field="x", min_value=0, max_value=1, default=0)  # 翻译标记位置
    y = FloatField(db_field="y", min_value=0, max_value=1, default=0)
    vertices = ListField(db_field="v", default=list)  # 外框位置百分比
    position_type = IntField(db_field="p", default=SourcePositionType.IN)
    # === 文本独有的参数 ===
    line_feed = BooleanField(db_field="lf", default=True)  # 区分人工分段，导出时不换行
    blank = BooleanField(db_field="b", default=False)  # 是否时空白，用于加速检索无空白的字段
    # === 独有参数结束 ===
    # 由自动标记、上传文件自动解析添加，用户手动标记的点为False
    machine = BooleanField(db_field="cm", default=True)
    possible_terms = ListField(
        ReferenceField(Term, reverse_delete_rule=PULL),
        db_field="pt",
        default=list,
    )
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)
    edit_time = DateTimeField(db_field="e", default=datetime.datetime.utcnow)

    meta = {"indexes": ["file", "blank", "rank"]}

    @classmethod
    def by_id(cls, id):
        source = cls.objects(id=id).first()
        if source is None:
            raise SourceNotExistError
        return source

    def find_terms(self):
        """寻找术语"""
        terms = Term.objects(term_bank__in=self.file.project.term_banks)
        self.possible_terms = []  # 清空可能的术语
        for term in terms:
            # 如果术语原文在翻译原文中，且可能的术语还没有，则增加
            if term.source in self.content and term not in self.possible_terms:
                self.possible_terms.append(term)
        self.save()

    def copy(self, source):
        """将其他Source的Translation和Tip复制到此Source，必须是空Source才能使用"""
        if self.translations().count() > 0:
            return  # 如果已有翻译，则不复制
        if self.blank:
            return  # 如果是空文本，则不复制
        # 更新自身信息
        self.update(
            x=source.x,
            y=source.y,
            vertices=source.vertices,
            line_feed=source.line_feed,
            blank=source.blank,
            machine=source.machine,
        )
        # 克隆翻译
        need_inc_targets = {
            target: {
                "inc_translated_source_count": False,
                "inc_checked_source_count": False,
            }
            for target in self.file.project.targets()
        }
        for translation in source.translations():
            Translation(
                source=self,
                target=translation.target,
                content=translation.content,
                user=translation.user,
                proofread_content=translation.proofread_content,
                proofreader=translation.proofreader,
                selected=translation.selected,
                selector=translation.selector,
                mt=translation.mt,
                create_time=translation.create_time,
                edit_time=translation.edit_time,
            ).save()
            # 判断是否要新增计数
            # 有翻译则新增
            need_inc_targets[translation.target][
                "inc_translated_source_count"
            ] = True  # noqa: E501
            if translation.selected:
                # 有选定的翻译则新增
                need_inc_targets[translation.target][
                    "inc_checked_source_count"
                ] = True  # noqa: E501
        for target, flag in need_inc_targets.items():
            # 更新计数缓存
            if flag["inc_translated_source_count"]:
                self.file.inc_cache("translated_source_count", 1, target=target)
            if flag["inc_checked_source_count"]:
                self.file.inc_cache("checked_source_count", 1, target=target)
        # 克隆Tip
        for tip in source.tips():
            Tip(
                source=self,
                target=tip.target,
                content=tip.content,
                user=tip.user,
                create_time=tip.create_time,
                edit_time=tip.edit_time,
            ).save()

    def move_ahead(self, next_source):
        """将Source移动到某个Source之前，None则移动到最后"""
        self.reload()  # 刷新缓存
        if self.file.type != FileType.IMAGE:
            raise FileTypeNotSupportError(gettext("只有图片文件能移动原文顺序"))
        # 如果设置为None则移动到最后一个
        if next_source is None:
            # 如果最后一个就是自己则不作处理
            last_source = Source.objects(file=self.file).order_by("-rank").first()
            if last_source == self:
                return True
            # 检查锁状态
            if self.file.source_moving:
                raise SourceMovingError
            self.file.update(source_moving=True)  # 上锁
            # 将自己和最后一个的Source之间的所有rank值-1
            Source.objects(file=self.file, rank__gt=self.rank).update(dec__rank=1)
            self.update(rank=last_source.rank)
            self.file.update(source_moving=False)  # 解锁
        # 移动到某个Source之前
        else:
            # 如果是str或者ObjectId则获取Source对象
            if isinstance(next_source, (str, ObjectId)):
                next_source = Source.by_id(next_source)
            # 如果不是同一个file下，则报不存在
            if next_source.file != self.file:
                raise SourceNotExistError
            # 如果是自身，不作处理
            if next_source == self:
                return True
            # 如果已经在前一个位置，不作处理
            if self.rank + 1 == next_source.rank:
                return True
            # 检查锁状态
            if self.file.source_moving:
                raise SourceMovingError
            self.file.update(source_moving=True)  # 上锁
            # 从后往前移动
            if self.rank > next_source.rank:
                Source.objects(
                    file=self.file,
                    rank__gte=next_source.rank,
                    rank__lt=self.rank,
                ).update(inc__rank=1)
                self.update(rank=next_source.rank)
            # 从前往后移动
            else:
                Source.objects(
                    file=self.file,
                    rank__gt=self.rank,
                    rank__lt=next_source.rank,
                ).update(dec__rank=1)
                self.update(rank=next_source.rank - 1)
            self.file.update(source_moving=False)  # 解锁
        return True

    def best_translation(self, target):
        """返回最佳翻译

        返回顺序如下
        1. 被选定的翻译
        2. 时间最新的翻译
        3. None
        """
        return self.translations(target=target).first()

    def create_translation(self, content: str, target, user, mt=False):
        """Translation.create(source=self)的快捷方式"""
        return Translation.create(
            content=content, source=self, target=target, user=user, mt=mt
        )

    def create_tip(self, content: str, target, user=None):
        """Tip.create(source=self)的快捷方式"""
        return Tip.create(content=content, source=self, target=target, user=user)

    def translations(self, target=None, skip=None, limit=None, order_by: list = None):
        translations = Translation.objects(source=self)
        if target:
            translations = translations.filter(target=target)
        # 排序处理
        translations = mongo_order(translations, order_by, default_translations_order)
        # 分页处理
        translations = mongo_slice(translations, skip, limit)
        return translations

    def tips(self, target=None, skip=None, limit=None, order_by: list = None):
        tips = Tip.objects(source=self)
        if target:
            tips = tips.filter(target=target)
        # 排序处理
        tips = mongo_order(tips, order_by, ["-edit_time"])
        # 分页处理
        tips = mongo_slice(tips, skip, limit)
        return tips

    def update_cache(self, cache_name, value):
        """更新某个缓存字段"""
        # 没有此属性跳过
        if not hasattr(self, cache_name):
            return
        self.update(**{cache_name: value})
        self.file.update_cache(cache_name, value)

    def clear(self):
        """删除原文，并更新缓存"""
        # 使用Translation的delete，修改计数
        for translation in self.translations():
            translation.clear()
        self.delete()
        self.file.inc_cache("source_count", -1)

    def to_api(self):
        return {
            "id": str(self.id),
            "content": self.content,
            "x": self.x,
            "y": self.y,
            "position_type": self.position_type,
            "machine": self.machine,
        }


class Translation(Document):
    source = ReferenceField(
        "Source", db_field="o", required=True, reverse_delete_rule=CASCADE
    )  # 所属原文
    target = ReferenceField(
        Target, db_field="t", required=True, reverse_delete_rule=CASCADE
    )  # 所属目标语言
    content = StringField(db_field="c", default="")  # 翻译内容
    user = ReferenceField("User", db_field="u", required=True)  # 翻译者
    proofread_content = StringField(db_field="p", default="")  # 校对内容
    proofreader = ReferenceField("User", db_field="pr")  # 校对者
    selected = BooleanField(db_field="s", required=True, default=False)  # 选定翻译
    selector = ReferenceField("User", db_field="sr")  # 选定者
    mt = BooleanField(db_field="mt", default=False)  # 是否由机器翻译
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)
    edit_time = DateTimeField(db_field="e", default=datetime.datetime.utcnow)

    meta = {
        "indexes": [
            "source",
            default_translations_order,
            {"fields": ["source", "target", "user"], "unique": True},
        ]
    }

    @classmethod
    def create(cls, content, source, target, user, mt=False):
        """新增翻译"""
        # 如果以前有自己的翻译则覆盖，没有则新增
        new_add = False  # 已有此翻译
        translation = cls.objects(
            source=source, user=user, target=target, mt=mt
        ).first()
        if translation:
            # 删除之前的翻译
            if content == "" and translation.proofread_content == "":
                translation.clear()
                return
        else:
            # 禁止创建空翻译
            if content == "":
                return
            new_add = True  # 本次新增的
            translation = cls(source=source, user=user, target=target, mt=mt)
        translation.content = content
        try:
            translation.save()
        except mongoengine.errors.NotUniqueError:
            raise TranslationNotUniqueError
        translation.update_cache("edit_time", datetime.datetime.utcnow())
        # 如果是唯一的翻译，且是新增的，且不是空白，则增加计数
        if (
            translation.other_translations().count() == 0
            and new_add
            and not source.blank
        ):
            source.file.inc_cache("translated_source_count", 1, target=target)
        translation.reload()
        return translation

    def unselect(self):
        """取消选中此翻译"""
        self.reload()  # 刷新缓存、状态，以免之前使用过unselect发生计数错误
        # 如果未被选中则跳过
        if not self.selected:
            return
        self.update(selected=False, unset__selector=1)
        self.other_translations().update(selected=False, unset__selector=1)
        self.source.file.inc_cache("checked_source_count", -1, target=self.target)
        self.update_cache("edit_time", datetime.datetime.utcnow())

    def select(self, user):
        """选中此翻译"""
        self.reload()  # 刷新缓存、状态，以免之前使用过unselect发生计数错误
        # 如果已被选中则跳过
        if self.selected:
            return
        inc_checked_source_count = True  # 增加计数
        selected_translation = self.selected_translation()  # 前一个被选中的翻译
        # 如果之前有已选择的翻译，则去除，并不增加计数
        if selected_translation:
            self.other_translations().update(selected=False, unset__selector=1)
            inc_checked_source_count = False  # 之前有则不增加计数
        self.update(selected=True, selector=user)
        if inc_checked_source_count and not self.source.blank:  # 如果原文为空则
            self.source.file.inc_cache("checked_source_count", 1, target=self.target)
        self.update_cache("edit_time", datetime.datetime.utcnow())

    def clear(self):
        """删除翻译，并更新缓存"""
        self.reload()  # 刷新缓存、状态，以免之前使用过unselect发生计数错误
        # 如果没有其他翻译，则修改缓存
        if self.selected:
            self.source.file.inc_cache("checked_source_count", -1, target=self.target)
        if self.other_translations().count() == 0:
            self.source.file.inc_cache(
                "translated_source_count", -1, target=self.target
            )
        self.delete()

    def update_cache(self, cache_name, value):
        """更新某个缓存字段"""
        # 没有此属性跳过
        if not hasattr(self, cache_name):
            return
        self.update(**{cache_name: value})
        self.source.file.update_cache(cache_name, value)

    def selected_translation(self):
        """获取被选中的翻译，同目标语言"""
        return Translation.objects(
            source=self.source, target=self.target, selected=True
        ).first()

    def other_translations(self):
        """返回其他的翻译，同目标语言"""
        return Translation.objects(
            source=self.source, target=self.target, id__ne=self.id
        )

    def to_api(self):
        return {
            "source_id": str(self.source.id),
            "id": str(self.id),
            "mt": self.mt,
            "content": self.content,
            "user": default(self.user, None, "to_api"),
            "proofread_content": self.proofread_content,
            "proofreader": default(self.proofreader, None, "to_api"),
            "selected": self.selected,
            "selector": default(self.selector, None, "to_api"),
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
            "target": self.target.to_api(),
        }


class Tip(Document):
    source = ReferenceField("Source", db_field="o", reverse_delete_rule=CASCADE)  # 所属原文
    target = ReferenceField(Target, db_field="t", reverse_delete_rule=CASCADE)  # 所属目标语言
    content = StringField(db_field="c", default="")
    user = ReferenceField("User", db_field="u")
    edit_time = DateTimeField(db_field="et", default=datetime.datetime.utcnow)
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)

    meta = {"indexes": ["source", "-edit_time"]}

    @classmethod
    def create(cls, content, source, target, user=None):
        """新增备注"""
        # 内容不能为空
        if content == "":
            raise TipEmptyError
        tip = cls(source=source, user=user, target=target)
        tip.content = content
        tip.save()
        return tip

    def to_api(self):
        return {
            "source_id": str(self.source.id),
            "id": str(self.id),
            "content": self.content,
            "user": self.user.to_api(),
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
        }
