from app.exceptions.project import LabelplusParseFailedError
import datetime

from bson import ObjectId
from io import BufferedReader
from flask import current_app
from flask_babel import gettext, lazy_gettext
from app.tasks.import_from_labelplus import import_from_labelplus
from mongoengine import (
    CASCADE,
    DENY,
    PULL,
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ListField,
    LongField,
    ReferenceField,
    StringField,
)
from app.utils.labelplus import load_from_labelplus
from app.core.rbac import (
    AllowApplyType,
    GroupMixin,
    PermissionMixin,
    RelationMixin,
    RoleMixin,
)
from app.exceptions import (
    FilenameDuplicateError,
    FilenameIllegalError,
    FolderNotExistError,
    LanguageNotExistError,
    NoPermissionError,
    ProjectFinishedError,
    ProjectHasDeletePlanError,
    ProjectHasFinishPlanError,
    ProjectNoDeletePlanError,
    ProjectNoFinishPlanError,
    ProjectNotExistError,
    ProjectNotFinishedError,
    ProjectSetNotExistError,
    TargetNotExistError,
    TargetAndSourceLanguageSameError,
)
from app.models.application import Application
from app.models.file import File, Filename
from app.models.invitation import Invitation
from app.models.language import Language
from app.models.target import Target
from app.models.term import TermBank
from app.models.output import Output
from app.tasks.file_parse import find_terms
from app.constants.file import (
    FileNotExistReason,
    FileType,
    FindTermsStatus,
    ParseStatus,
)
from app.constants.project import (
    ImportFromLabelplusErrorType,
    ImportFromLabelplusStatus,
    ProjectStatus,
)
from app.utils.mongo import mongo_order, mongo_slice
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.team import Team


class ProjectAllowApplyType(AllowApplyType):
    """
    允许谁申请加入
    """

    TEAM_USER = 3

    # 合并复写details
    details = {
        **AllowApplyType.details,
        **{"TEAM_USER": {"name": lazy_gettext("仅团队成员")}},
    }


class ProjectPermission(PermissionMixin):
    FINISH = 1010
    ADD_FILE = 1020
    MOVE_FILE = 1030
    RENAME_FILE = 1040
    DELETE_FILE = 1050
    OUTPUT_TRA = 1060
    # 1070 空余，原为导出源图
    ADD_LABEL = 1080
    MOVE_LABEL = 1090
    DELETE_LABEL = 1100
    ADD_TRA = 1110
    DELETE_TRA = 1120
    PROOFREAD_TRA = 1130
    CHECK_TRA = 1140
    ADD_TARGET = 1150
    CHANGE_TARGET = 1160
    DELETE_TARGET = 1170

    details = {
        # RBAC默认权限介绍
        **PermissionMixin.details,
        # RBAC默认权限介绍（覆盖）
        "ACCESS": {"name": lazy_gettext("访问项目")},
        "DELETE": {"name": lazy_gettext("删除项目")},
        "CHANGE": {"name": lazy_gettext("设置项目")},
        # 项目级权限介绍
        "FINISH": {"name": lazy_gettext("完结项目")},
        "ADD_FILE": {"name": lazy_gettext("上传图片")},
        "MOVE_FILE": {"name": lazy_gettext("移动文件")},
        "RENAME_FILE": {"name": lazy_gettext("修改图片名称")},
        "DELETE_FILE": {"name": lazy_gettext("删除图片")},
        "OUTPUT_TRA": {"name": lazy_gettext("导出翻译")},
        "ADD_LABEL": {"name": lazy_gettext("新建图片标记")},
        "MOVE_LABEL": {"name": lazy_gettext("移动图片标记")},
        "DELETE_LABEL": {"name": lazy_gettext("删除图片标记")},
        "ADD_TRA": {"name": lazy_gettext("新增翻译")},
        "DELETE_TRA": {"name": lazy_gettext("删除他人翻译")},
        "PROOFREAD_TRA": {"name": lazy_gettext("校对翻译")},
        "CHECK_TRA": {
            "name": lazy_gettext("选定翻译"),
            "intro": lazy_gettext("将某条翻译指定导出项"),
        },
        "ADD_TARGET": {"name": lazy_gettext("新增目标语言")},
        "CHANGE_TARGET": {"name": lazy_gettext("修改目标语言")},
        "DELETE_TARGET": {"name": lazy_gettext("删除目标语言")},
    }


class ProjectRole(RoleMixin, Document):
    permission_cls = ProjectPermission
    group = ReferenceField("Project", db_field="g")
    system_role_data = [
        {
            "name": gettext("创建人"),
            "permissions": [
                ProjectPermission.ACCESS,
                ProjectPermission.CHANGE,
                ProjectPermission.FINISH,
                ProjectPermission.DELETE,
                ProjectPermission.ADD_FILE,
                ProjectPermission.MOVE_FILE,
                ProjectPermission.RENAME_FILE,
                ProjectPermission.DELETE_FILE,
                ProjectPermission.OUTPUT_TRA,
                ProjectPermission.ADD_LABEL,
                ProjectPermission.MOVE_LABEL,
                ProjectPermission.DELETE_LABEL,
                ProjectPermission.ADD_TRA,
                ProjectPermission.DELETE_TRA,
                ProjectPermission.PROOFREAD_TRA,
                ProjectPermission.CHECK_TRA,
                ProjectPermission.CHECK_USER,
                ProjectPermission.INVITE_USER,
                ProjectPermission.CHANGE_USER_REMARK,
                ProjectPermission.CHANGE_USER_ROLE,
                ProjectPermission.DELETE_USER,
                ProjectPermission.ADD_TARGET,
                ProjectPermission.CHANGE_TARGET,
                ProjectPermission.DELETE_TARGET,
            ],
            "level": 500,
            "system_code": "creator",
        },
        {
            "name": gettext("管理员"),
            "permissions": [
                ProjectPermission.ACCESS,
                ProjectPermission.CHANGE,
                ProjectPermission.FINISH,
                ProjectPermission.DELETE,
                ProjectPermission.ADD_FILE,
                ProjectPermission.MOVE_FILE,
                ProjectPermission.RENAME_FILE,
                ProjectPermission.DELETE_FILE,
                ProjectPermission.OUTPUT_TRA,
                ProjectPermission.ADD_LABEL,
                ProjectPermission.MOVE_LABEL,
                ProjectPermission.DELETE_LABEL,
                ProjectPermission.ADD_TRA,
                ProjectPermission.DELETE_TRA,
                ProjectPermission.PROOFREAD_TRA,
                ProjectPermission.CHECK_TRA,
                ProjectPermission.INVITE_USER,
                ProjectPermission.CHECK_USER,
                ProjectPermission.CHANGE_USER_REMARK,
                ProjectPermission.CHANGE_USER_ROLE,
                ProjectPermission.DELETE_USER,
                ProjectPermission.ADD_TARGET,
                ProjectPermission.CHANGE_TARGET,
                ProjectPermission.DELETE_TARGET,
            ],
            "level": 400,
            "system_code": "admin",
        },
        {
            "name": gettext("监理"),
            "permissions": [
                ProjectPermission.ACCESS,
                ProjectPermission.ADD_FILE,
                ProjectPermission.MOVE_FILE,
                ProjectPermission.RENAME_FILE,
                ProjectPermission.DELETE_FILE,
                ProjectPermission.OUTPUT_TRA,
                ProjectPermission.ADD_LABEL,
                ProjectPermission.MOVE_LABEL,
                ProjectPermission.DELETE_LABEL,
                ProjectPermission.ADD_TRA,
                ProjectPermission.DELETE_TRA,
                ProjectPermission.PROOFREAD_TRA,
                ProjectPermission.CHECK_TRA,
                ProjectPermission.INVITE_USER,
                ProjectPermission.CHECK_USER,
                ProjectPermission.DELETE_USER,
                ProjectPermission.CHANGE_USER_REMARK,
                ProjectPermission.CHANGE_USER_ROLE,
            ],
            "level": 300,
            "system_code": "coordinator",
        },
        {
            "name": gettext("校对"),
            "permissions": [
                ProjectPermission.ACCESS,
                ProjectPermission.OUTPUT_TRA,
                ProjectPermission.ADD_LABEL,
                ProjectPermission.MOVE_LABEL,
                ProjectPermission.DELETE_LABEL,
                ProjectPermission.ADD_TRA,
                ProjectPermission.PROOFREAD_TRA,
                ProjectPermission.CHECK_TRA,
            ],
            "level": 200,
            "system_code": "proofreader",
        },
        {
            "name": gettext("翻译"),
            "permissions": [
                ProjectPermission.ACCESS,
                ProjectPermission.OUTPUT_TRA,
                ProjectPermission.ADD_LABEL,
                ProjectPermission.MOVE_LABEL,
                ProjectPermission.DELETE_LABEL,
                ProjectPermission.ADD_TRA,
            ],
            "level": 200,
            "system_code": "translator",
        },
        {
            "name": gettext("嵌字"),
            "permissions": [
                ProjectPermission.ACCESS,
                ProjectPermission.OUTPUT_TRA,
                ProjectPermission.ADD_LABEL,
                ProjectPermission.MOVE_LABEL,
                ProjectPermission.DELETE_LABEL,
            ],
            "level": 200,
            "system_code": "picture_editor",
        },
        {
            "name": gettext("见习翻译"),
            "permissions": [ProjectPermission.ACCESS, ProjectPermission.ADD_TRA],
            "level": 100,
            "system_code": "supporter",
        },
    ]


class ProjectSet(Document):
    """项目集"""

    name = StringField(db_field="n", required=True)  # 集合名
    intro = StringField(db_field="i", default="")  # 项目集介绍
    team = ReferenceField("Team", db_field="t", required=True)
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)
    edit_time = DateTimeField(
        db_field="et", required=True, default=datetime.datetime.utcnow
    )
    default = BooleanField(db_field="d", required=True, default=False)  # 是否是默认项目集

    @classmethod
    def create(cls, name, team, default=False):
        return cls(name=name, team=team, default=default).save()

    def clear(self):
        # TODO: 将项目集内项目移动到默认项目集
        self.delete()

    @classmethod
    def by_id(cls, id):
        set = cls.objects(id=id).first()
        if set is None:
            raise ProjectSetNotExistError()
        return set

    def to_api(self):
        """
        @apiDefine TeamProjectSetInfoModel
        @apiSuccess {String} id ID
        @apiSuccess {String} name 名称
        @apiSuccess {String} intro 介绍
        @apiSuccess {Number} type 项目集类型（暂时没有用）
        @apiSuccess {String} create_time 创建时间
        @apiSuccess {String} edit_time 修改时间

        """
        return {
            "id": str(self.id),
            "name": self.name,
            "intro": self.intro,
            "default": self.default,
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
        }


class Project(GroupMixin, Document):
    name = StringField(db_field="n", required=True)  # 项目名
    intro = StringField(db_field="i", default="")  # 项目介绍
    team = ReferenceField("Team", db_field="t", required=True)  # 所属团队
    project_set = ReferenceField("ProjectSet", db_field="ps", required=True)  # 所属集合
    default_role = ReferenceField(
        "ProjectRole", db_field="dr", reverse_delete_rule=DENY
    )
    max_user = IntField(db_field="u", required=True, default=100000)  # 最大用户数
    source_name = StringField(db_field="sn")  # 作品原名
    target_name = StringField(db_field="tn")  # 作品译名
    source_language = ReferenceField(  # 源语言
        Language, db_field="ol", required=True, reverse_delete_rule=DENY
    )
    tags = ListField(StringField(), db_field="ta", default=list)  # 项目标签
    status = IntField(db_field="st", default=ProjectStatus.WORKING)  # 项目状态
    system_finish_time = DateTimeField(db_field="ft")  # 项目被系统正式完结时间
    plan_finish_time = DateTimeField(db_field="pft")  # 用户操作计划完结时间
    plan_delete_time = DateTimeField(db_field="pdt")  # 用户操作计划删除时间

    # == 术语库 ==
    _term_banks = ListField(
        ReferenceField(TermBank, reverse_delete_rule=PULL),
        db_field="tb",
        default=list,
    )
    need_find_terms = BooleanField(db_field="nft", default=False)

    # == 解析原文 ==
    ocring = BooleanField(db_field="oc", default=False)  # 是否正在进行项目级解析

    # == 缓存 ==
    target_count = IntField(db_field="tc", required=True, default=0)  # 目标语言数量缓存
    folder_count = IntField(db_field="fo", required=True, default=0)  # 文件数量
    file_count = IntField(db_field="fc", required=True, default=0)  # 文件数量
    file_size = LongField(db_field="fs", required=True, default=0)  # 文件大小，单位KB
    source_count = IntField(db_field="sc", required=True, default=0)  # 原文数量
    # targets汇总的缓存
    translated_source_count = IntField(db_field="tsc", default=0)  # 已翻译的原文数量
    checked_source_count = IntField(db_field="csc", default=0)  # 已校对的原文数量

    # == 从 LP 导入 ==
    import_from_labelplus_status = IntField(
        db_field="is", default=ImportFromLabelplusStatus.SUCCEEDED
    )
    import_from_labelplus_percent = IntField(db_field="ip", default=0)
    import_from_labelplus_error_type = IntField(
        db_field="ie", default=ImportFromLabelplusErrorType.UNKNOWN
    )
    import_from_labelplus_txt = StringField(db_field="it", default="")

    # == GroupMixin ==
    default_role_system_code = "translator"
    role_cls = ProjectRole
    permission_cls = ProjectPermission
    allow_apply_type_cls = ProjectAllowApplyType

    @classmethod
    def create(
        cls,
        name: str,
        team: "Team",
        project_set: ProjectSet = None,
        default_role=None,
        allow_apply_type=None,
        application_check_type=None,
        creator=None,
        source_language=None,
        target_languages=None,
        intro="",
        labelplus_txt=None,
    ) -> "Project":
        """创建一个项目"""
        # 尝试解析 labelplus 文本
        if labelplus_txt:
            try:
                load_from_labelplus(labelplus_txt)
            except Exception:
                raise LabelplusParseFailedError
        # 语言默认值
        if source_language is None:
            source_language = Language.by_code("ja")
        if target_languages is None:
            target_languages = [Language.by_code("zh-CN")]
        elif isinstance(target_languages, list) and len(target_languages) == 0:
            target_languages = [Language.by_code("zh-CN")]
        # 将目标语言转换为列表
        if isinstance(target_languages, Language):
            target_languages = [target_languages]
        else:
            # 目标语言去重
            target_languages = list(set(target_languages))
        # 检查目标语言是否都存在
        for target_language in target_languages:
            if not isinstance(target_language, Language):
                raise LanguageNotExistError(gettext("必须是Language对象"))
        # 检查目标语言和源语言是否重复
        if source_language in target_languages:
            raise TargetAndSourceLanguageSameError
        # 检查项目集
        if project_set is None:
            project_set = team.default_project_set
        # 项目集的团队和项目的团队不一致
        if project_set.team != team:
            raise ProjectSetNotExistError
        # 创建项目
        project = cls(
            name=name,
            team=team,
            project_set=project_set,
            source_language=source_language,
        )
        # 设置默认角色
        if default_role:
            project.default_role = default_role
        else:
            project.default_role = cls.default_system_role()
        # 设置其他选项
        if allow_apply_type:
            project.allow_apply_type = allow_apply_type
        if application_check_type:
            project.application_check_type = application_check_type
        project.intro = intro
        # 保存团队
        project.save()
        # 创建项目目标语言对象
        targets = []
        for target_language in target_languages:
            target = Target.create(project=project, language=target_language)
            targets.append(target)
        # 添加创建人
        if creator:
            creator.join(project, role=cls.role_cls.by_system_code("creator"))
        # 通过 Labelplus 数据创建文件及翻译
        if labelplus_txt and creator and len(targets) == 1:
            project.update(
                import_from_labelplus_txt=labelplus_txt,
                import_from_labelplus_status=ImportFromLabelplusStatus.PENDING,
                import_from_labelplus_percent=0,
            )
            import_from_labelplus(str(project.id))
        project.reload()
        return project

    def targets(self, language=None):
        """获取所有目标语言"""
        targets = Target.objects(project=self)
        if language:
            targets = targets.filter(language=language)
        return targets

    def target_by_id(self, id) -> Target:
        """通过id获取目标语言"""
        target = Target.objects(id=id, project=self).first()
        if target is None:
            raise TargetNotExistError
        return target

    @property
    def relation_cls(self):
        return ProjectUserRelation

    @property
    def term_banks(self):
        """项目所用的术语库"""
        return self._term_banks

    @term_banks.setter
    def term_banks(self, value: list):
        """设置项目所用的术语库"""
        self._term_banks = value
        self.need_find_terms = True

    def find_terms(self):
        """异步刷新所有文件的可能术语"""
        # 如果有设置术语库，进行寻找术语任务
        if len(self._term_banks) > 0:
            for file in self.files(type_exclude=FileType.FOLDER):
                # celery任务
                run_sync = current_app.config.get("TESTING", False)  # 如果测试则同步执行
                result = find_terms(str(file.id), run_sync=run_sync)
                # 设置文件状态
                file.update(
                    find_terms_task_id=result.task_id,
                    find_terms_status=FindTermsStatus.QUEUING,
                )
        # 关闭提示
        self.need_find_terms = False
        self.save()

    def inc_cache(self, cache_name, step, target=None):
        # 0则不请求数据库
        if step == 0:
            return
        # 翻译缓存
        if cache_name in ["translated_source_count", "checked_source_count"]:
            if target is None:
                raise ValueError("更新翻译缓存数据必须指定target")
            target.update(**{"inc__" + cache_name: step})
            self.update(**{"inc__" + cache_name: step})
        # 其他缓存
        else:
            # 没有此属性跳过
            if not hasattr(self, cache_name):
                return
            # 更新项目缓存
            self.update(**{"inc__" + cache_name: step})

    def update_cache(self, cache_name, value):
        """更新某个缓存字段"""
        # 没有此属性跳过
        if not hasattr(self, cache_name):
            return
        # 更新自身缓存
        self.update(**{cache_name: value})
        # edit_time 需要同步修改 ProjectSet 和 Team 的
        if cache_name == "edit_time":
            self.project_set.update(**{cache_name: value})
            self.team.update(**{cache_name: value})

    def is_allow_apply(self, user) -> bool:
        """是否允许此用户申请加入"""
        # 只允许团队成员申请加入
        if self.allow_apply_type == ProjectAllowApplyType.TEAM_USER:
            # 是团队成员
            if user.get_relation(self.team):
                return True
            else:
                raise NoPermissionError(gettext("只允许项目所属团队成员申请加入"))
        return super().is_allow_apply(user)

    def move_to_project_set(self, project_set):
        """
        将项目添加到本项目集

        :param project_set: 如果为None，则移出项目集
        :return:
        """
        if project_set.team != self.team:
            raise ProjectSetNotExistError
        self.project_set = project_set
        self.save()

    def create_folder(self, name, parent=None):
        """创建文件夹"""
        # 确认父级文件夹是否存在于本项目
        if parent is not None:
            parent = self.get_folder(parent)
        # 检查是否有同名文件
        folder_name = Filename(name, folder=True)
        old_folder = self.get_files(name=folder_name.name, parent=parent).first()
        # 有同名文件/文件夹，报错
        if old_folder:
            raise FilenameDuplicateError
        # 新建文件夹
        folder = File(
            name=folder_name.name,
            project=self,
            parent=parent,
            type=folder_name.file_type,
            sort_name=folder_name.sort_name,
        ).save()
        # 创建FileTargetCache
        for target in self.targets():
            folder.create_target_cache(target)
        folder.inc_cache("folder_count", 1, update_self=False)
        return folder

    def create_file(self, name: str, parent: File = None) -> File:
        """
        创建文件

        [对于存在同名文件的策略]
        图片：返回同名文件对象
        文本：返回一个新建的未激活修订版
        其他类型：报错

        :param name: 文件名
        :param parent: 所属文件夹，顶层则为None
        :return:
        """
        # 确认父级是文件夹且存在于本项目
        if parent is not None:
            parent = self.get_folder(parent)
        filename = Filename(name)
        # 不支持的后缀
        supported_types = (
            FileType.TEST_SUPPORTED
            if current_app.config.get("TESTING", False)
            else FileType.SUPPORTED
        )
        if filename.file_type not in supported_types:
            raise FilenameIllegalError(gettext("暂不支持的文件格式"))
        # 检查是否有同名文件
        file: File = self.get_files(name=filename.name, parent=parent).first()
        # 有同名文件
        if file:
            # 图片，什么都不做
            if file.type == FileType.IMAGE:
                pass
            # 文本，创建新修订版
            elif file.type == FileType.TEXT:
                file = file.create_revision()  # 创建新修订版
                file.activate_revision()  # 激活此修订版
            # 文本夹，与文件夹重名报错
            elif file.type == FileType.FOLDER:
                raise FilenameDuplicateError
            else:
                raise FilenameDuplicateError
        # 没有同名文件
        else:
            # 新建文件对象
            file = File(
                name=filename.name,
                project=self,
                parent=parent,
                type=filename.file_type,
                sort_name=filename.sort_name,
                file_not_exist_reason=FileNotExistReason.NOT_UPLOAD,
            ).save()
            # 创建FileTargetCache
            for target in self.targets():
                file.create_target_cache(target)
            # 更新文件个数
            file.inc_cache("file_count", 1, update_self=False)
        return file

    def upload(self, filename: str, real_file: BufferedReader, parent=None):
        """
        上传文件

        :param filename: 文件名
        :param real_file: 文件实体
        :param parent: 所属文件夹，顶层则为None
        :return:
        """
        # 创建文件对象
        file = self.create_file(filename, parent)
        file.upload_real_file(real_file)
        return file

    def upload_from_zip(self):
        """从zip导入项目"""

    def upload_from_github(self):
        """从github导入项目"""

    @classmethod
    def by_id(cls, id):
        project = cls.objects(id=id).first()
        if project is None:
            raise ProjectNotExistError()
        return project

    def get_files(self, name, parent="all", activated=True):
        """通过文件名获取文件或文件夹(大小写不敏感)，默认仅获取激活的修订版"""
        file = File.objects(name__iexact=name, project=self)
        # 限制文件夹
        if parent != "all":
            if parent is not None:
                parent = self.get_folder(parent)
            file = file.filter(parent=parent)
        # 限制修订版，将activated设为'all'以搜索所有修订版
        if isinstance(activated, bool):
            file = file.filter(activated=activated)
        return file

    def get_folder(self, folder):
        """
        尝试获取本项目下的文件夹，检查文件夹是否存在于本项目
        如没有则raise FolderNotExistError

        :param folder: 支持 字符串、ObjectId或File对象
        :return:
        """
        # 是字符串、ObjectId，则尝试获取File对象
        if isinstance(folder, (str, ObjectId)):
            folder = File.objects(id=folder, project=self, type=FileType.FOLDER).first()
            # 文件夹不存在报错
            if folder is None:
                raise FolderNotExistError
        # 是File对象，则检查是否属于本项目
        elif isinstance(folder, File):
            # 不属于本项目或不是文件夹，报错
            if folder.project != self or folder.type != FileType.FOLDER:
                raise FolderNotExistError
        # 其他类型直接报错
        else:
            raise ValueError(
                "folder参数 需要是 字符串、ObjectId或File对象，所给值为" + f"[{type(folder)}]{folder}"
            )
        return folder

    def files(
        self,
        skip=None,
        limit=None,
        order_by: list = None,
        parent="all",
        type_only=None,
        type_exclude=None,
        word: str = None,
        file_ids_include: List[str] = None,
        file_ids_exclude: List[str] = None,
    ) -> List[File]:
        """
        获取所有文件

        :param skip: 跳过的数量
        :param limit: 限制的数量
        :param order_by: 排序
        :param parent: 父文件夹，默认'all'查询所有files
        :param type_only: 只显示某些类型
        :param type_exclude: 排除某些类型
        :return:
        """
        files = File.objects(project=self, activated=True)
        if word is not None:
            files = files.filter(name__icontains=word)
        # 父文件夹
        if parent != "all":
            # 确认父级文件夹是否存在于本项目
            if parent is not None:
                parent = self.get_folder(parent)
            files = files.filter(parent=parent)
        # 只显示文件夹
        if type_only is not None:
            if isinstance(type_only, list):
                files = files.filter(type__in=type_only)
            else:
                files = files.filter(type=type_only)
        # 只显示文件
        if type_exclude is not None:
            if isinstance(type_exclude, list):
                files = files.filter(type__nin=type_exclude)
            else:
                files = files.filter(type__ne=type_exclude)
        # 限制 ids
        if file_ids_include:
            files = files.filter(id__in=file_ids_include)
        if file_ids_exclude:
            files = files.filter(id__nin=file_ids_exclude)
        # 排序处理
        files = mongo_order(files, order_by, ["dir_sort_name", "type", "sort_name"])
        # 分页处理
        files = mongo_slice(files, skip, limit)
        return files

    def plan_finish(self):
        """计划完结项目"""
        # 项目已有完结/销毁计划
        if self.status == ProjectStatus.PLAN_DELETE:
            raise ProjectHasDeletePlanError
        if self.status == ProjectStatus.PLAN_FINISH:
            raise ProjectHasFinishPlanError
        # 项目已经完结了
        if self.status == ProjectStatus.FINISHED:
            raise ProjectFinishedError
        # 设置计划完结时间
        self.update(
            status=ProjectStatus.PLAN_FINISH,
            plan_finish_time=datetime.datetime.utcnow(),
        )
        self.reload()

    def cancel_finish_plan(self):
        """取消完结项目计划"""
        # 检查是否有完结计划
        if self.status != ProjectStatus.PLAN_FINISH:
            raise ProjectNoFinishPlanError
        # 恢复到工作状态，并删除计划完结时间
        self.update(
            status=ProjectStatus.WORKING,
            unset__plan_finish_time=1,
        )
        self.reload()

    def finish(self):
        """完结项目"""
        # 必须处于进行中或完结计划中
        # TODO: 弃用 ProjectStatus.PLAN_FINISH，并同步修改测试
        if self.status not in [ProjectStatus.PLAN_FINISH, ProjectStatus.WORKING]:
            # TODO: 使用 ProjectCanNotFinishError 替换，并同步修改测试
            raise ProjectNoFinishPlanError
        # 物理删除储存中文件，并将文件、文件夹大小归零
        for file in self.files():
            file.file_size = 0
            # 对文件的特殊处理
            if file.type != FileType.FOLDER:
                # 删除对象源文件
                file.delete_real_file(
                    update_cache=False,
                    file_not_exist_reason=FileNotExistReason.FINISH,
                )
            file.save()
        # 物理删除所有导出的output
        Output.delete_real_files(self.outputs())
        self.update(
            file_size=0,
            status=ProjectStatus.FINISHED,
            system_finish_time=datetime.datetime.utcnow(),
        )
        self.reload()

    def resume(self):
        """从完结状态重新开始项目"""
        if self.status != ProjectStatus.FINISHED:
            raise ProjectNotFinishedError
        self.update(
            status=ProjectStatus.WORKING,
            unset__system_finish_time=1,
            unset__plan_finish_time=1,
        )
        self.reload()

    def plan_delete(self):
        """计划销毁项目"""
        # 项目已有完结/销毁计划
        if self.status == ProjectStatus.PLAN_DELETE:
            raise ProjectHasDeletePlanError
        if self.status == ProjectStatus.PLAN_FINISH:
            raise ProjectHasFinishPlanError
        # 设置计划删除时间
        self.update(
            status=ProjectStatus.PLAN_DELETE,
            plan_delete_time=datetime.datetime.utcnow(),
        )
        self.reload()

    def cancel_delete_plan(self):
        """取消销毁项目计划"""
        # 检查是否有销毁计划
        if self.status != ProjectStatus.PLAN_DELETE:
            raise ProjectNoDeletePlanError
        # 如果有系统完结时间，说明这个项目之前已经正式完结了
        # 恢复到完结状态，并删除计划销毁时间
        if self.system_finish_time:
            self.update(status=ProjectStatus.FINISHED, unset__plan_delete_time=1)
        # 恢复到工作状态，并删除计划销毁时间
        else:
            self.update(status=ProjectStatus.WORKING, unset__plan_delete_time=1)
        self.reload()

    def outputs(self):
        """所有导出"""
        outputs = Output.objects(project=self).order_by("-create_time")
        return outputs

    @staticmethod
    def batch_to_api(
        projects,
        user,
        /,
        *,
        inherit_admin_team=None,
        with_team=True,
        with_project_set=True,
    ):
        """
        批量转换 projects 到 api 格式

        :param inherit_admin_team 从某个项目继承权限，此时需要所有 projects 都在一个 team 内
        """
        from app.models.team import TeamPermission

        # 获取团队用户关系
        relations = ProjectUserRelation.objects(group__in=projects, user=user)
        # 构建字典用于快速匹配
        project_roles_data = {}
        for relation in relations:
            project_roles_data[str(relation.group.id)] = relation.role.to_api()
        # 检查是否自动成为项目管理员权限
        role_from_team_data = None
        if inherit_admin_team and user.can(
            inherit_admin_team, TeamPermission.AUTO_BECOME_PROJECT_ADMIN
        ):
            role_from_team_data = ProjectRole.by_system_code("admin").to_api()
        # 构建数据
        data = []
        for project in projects:
            project_data = project.to_api(
                with_team=with_team, with_project_set=with_project_set
            )
            project_data["role"] = None
            project_role_data = project_roles_data.get(str(project.id))
            if project_role_data:
                project_data["role"] = project_role_data
            else:
                if role_from_team_data:
                    project_data["role"] = role_from_team_data
                    project_data["auto_become_project_admin"] = True
            data.append(project_data)
        return data

    def clear(self):
        """物理删除项目"""
        for file in self.files(type_exclude=FileType.FOLDER):
            file.delete_real_file(init_obj=False)
        Output.delete_real_files(self.outputs())
        self.delete()

    def to_labelplus(
        self,
        /,
        *,
        target,
        file_ids_include: List[str] = None,
        file_ids_exclude: List[str] = None,
    ):
        """将图片文件的翻译导出成Labelplus格式"""
        # Labelplus翻译文件头格式
        data = (
            "1,0\r\n"  # 版本
            + "-\r\n"
            + gettext("框内")
            + "\r\n"  # 标签分组
            + gettext("框外")
            + "\r\n"
            + "-\r\n"
            + gettext("可使用 LabelPlus Photoshop 脚本导入 psd 中")
            + "\r\n"  # 注释
        )
        # 遍历所有图片
        for file in self.files(
            type_only=FileType.IMAGE,
            file_ids_include=file_ids_include,
            file_ids_exclude=file_ids_exclude,
        ):
            data += file.to_labelplus(target=target)
        return data
    
    def to_output_json(self):
        data = {
            "name": self.name,
            "intro": self.intro,
            "default_role": self.default_role.system_code,
            "allow_apply_type": self.allow_apply_type,
            "application_check_type": self.application_check_type,
            "is_need_check_application": self.is_need_check_application(),
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
            "source_language": self.source_language.code,
            "target_languages": [target.language.code for target in self.targets()],
        }
        return data

    def to_api(self, /, *, user=None, with_team=True, with_project_set=True):
        """
        @apiDefine ProjectPublicInfoModel
        @apiSuccess {String} group_type 团体类型
        @apiSuccess {String} id ID
        @apiSuccess {String} name 名称
        @apiSuccess {String} intro 介绍
        @apiSuccess {Number} max_user 最大用户数
        @apiSuccess {Number} status 项目状态
            WORKING = 0  # 进行中
            FINISHED = 1  # 已完结
            PLAN_FINISH = 2  # 处于完结计划
            PLAN_DELETE = 3  # 处于销毁计划
        @apiSuccess {String} default_role 默认角色 ID
        @apiSuccess {String} allow_apply_type 允许申请的类型
        @apiSuccess {String} application_check_type 如何处理申请
        @apiSuccess {String} is_need_check_application 是否需要确认申请
        @apiSuccess {String} role 用户在团体中的角色
        @apiSuccess {Boolean} auto_become_project_admin admin权限是否是继承自团队
        @apiSuccess {String} create_time 创建时间
        @apiSuccess {String} edit_time 修改时间
        """
        # 如果给予 user 则获取用户相关信息（角色等）
        auto_become_project_admin = False
        role = None
        if user:
            role = user.get_role(self)
            if role:
                role = role.to_api()
                relation = user.get_relation(self)
                # 有 role 但是没有关系，则说明是继承自团队
                if relation is None:
                    auto_become_project_admin = True
        data = {
            "group_type": "project",
            "id": str(self.id),
            "name": self.name,
            "intro": self.intro,
            "max_user": self.max_user,
            "status": self.status,
            "user_count": self.user_count,
            "default_role": str(self.default_role.id),
            "allow_apply_type": self.allow_apply_type,
            "application_check_type": self.application_check_type,
            "is_need_check_application": self.is_need_check_application(),
            "role": role,
            "auto_become_project_admin": auto_become_project_admin,
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
            "source_language": self.source_language.to_api(),
            "target_count": self.target_count,
            "source_count": self.source_count,
            "translated_source_count": self.translated_source_count,
            "checked_source_count": self.checked_source_count,
            "import_from_labelplus_status": self.import_from_labelplus_status,
            "import_from_labelplus_percent": self.import_from_labelplus_percent,
            "import_from_labelplus_error_type": self.import_from_labelplus_error_type,
            "import_from_labelplus_error_type_name": ImportFromLabelplusErrorType.get_detail_by_value(
                self.import_from_labelplus_error_type, "name"
            ),
        }
        if with_team:
            data["team"] = self.team.to_api(user=user)
        if with_project_set:
            data["project_set"] = self.project_set.to_api()
        return data


Project.register_delete_rule(ProjectRole, "group", CASCADE)
Project.register_delete_rule(Application, "group", CASCADE)
Project.register_delete_rule(Invitation, "group", CASCADE)
Project.register_delete_rule(File, "project", CASCADE)
Project.register_delete_rule(Target, "project", CASCADE)
Project.register_delete_rule(Output, "project", CASCADE)

ProjectSet.register_delete_rule(Project, "project_set", DENY)


class ProjectUserRelation(RelationMixin, Document):
    user = ReferenceField("User", db_field="u", required=True)
    group = ReferenceField(
        "Project", db_field="g", required=True, reverse_delete_rule=CASCADE
    )
    role = ReferenceField("ProjectRole", db_field="r", required=True)
