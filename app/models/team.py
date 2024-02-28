import datetime
import re

from flask import current_app
from flask_babel import gettext, lazy_gettext
from mongoengine import (
    CASCADE,
    DENY,
    Document,
    IntField,
    ReferenceField,
    StringField,
    DateTimeField,
)

from app import oss
from app.core.rbac import (
    AllowApplyType,
    GroupMixin,
    PermissionMixin,
    RelationMixin,
    RoleMixin,
)
from app.exceptions import (
    TeamNameLengthError,
    TeamNameRegexError,
    TeamNameRegisteredError,
    TeamNotExistError,
)
from app.models.application import Application
from app.models.invitation import Invitation
from app.models.project import Project, ProjectRole, ProjectSet
from app.models.term import TermBank
from app.regexs import TEAM_NAME_REGEX
from app.utils.mongo import mongo_order, mongo_slice


class TeamPermission(PermissionMixin):
    AUTO_BECOME_PROJECT_ADMIN = 1010
    CREATE_TERM_BANK = 1020
    ACCESS_TERM_BANK = 1030
    CHANGE_TERM_BANK = 1040
    DELETE_TERM_BANK = 1050
    CREATE_TERM = 1060
    CHANGE_TERM = 1070
    DELETE_TERM = 1080
    CREATE_PROJECT = 1090
    CREATE_PROJECT_SET = 1100
    CHANGE_PROJECT_SET = 1110
    DELETE_PROJECT_SET = 1120
    USE_OCR_QUOTA = 1130
    USE_MT_QUOTA = 1140
    INSIGHT = 1150

    details = {
        # RBAC默认权限介绍
        **PermissionMixin.details,
        # RBAC默认权限介绍（覆盖）
        "ACCESS": {"name": lazy_gettext("访问团队")},
        "DELETE": {"name": lazy_gettext("解散团队")},
        "CHANGE": {"name": lazy_gettext("设置团队")},
        # 团队级权限介绍
        "AUTO_BECOME_PROJECT_ADMIN": {
            "name": lazy_gettext("管理项目"),
            "intro": lazy_gettext("自动获得团队内所有项目的管理员权限"),
        },
        "CREATE_TERM_BANK": {
            "name": lazy_gettext("创建术语库"),
            "intro": lazy_gettext("在团队内创建术语库"),
        },
        "ACCESS_TERM_BANK": {
            "name": lazy_gettext("查看他人术语库"),
            "intro": lazy_gettext("若无此权限只能查看自己创建的术语库中的术语"),
        },
        "CHANGE_TERM_BANK": {
            "name": lazy_gettext("设置他人术语库"),
            "intro": lazy_gettext("若无此权限只能修改自己创建的术语库设置"),
        },
        "DELETE_TERM_BANK": {
            "name": lazy_gettext("删除他人术语库"),
            "intro": lazy_gettext("若无此权限只能删除自己创建的术语库"),
        },
        "CREATE_TERM": {
            "name": lazy_gettext("在他人术语库中增加术语"),
            "intro": lazy_gettext("若无此权限只能在自己创建的术语库中增加术语"),
        },
        "CHANGE_TERM": {
            "name": lazy_gettext("修改他人术语"),
            "intro": lazy_gettext(
                "若无此权限只能修改自己创建的术语或自己术语库中的术语"
            ),
        },
        "DELETE_TERM": {
            "name": lazy_gettext("删除他人术语"),
            "intro": lazy_gettext(
                "若无此权限只能删除自己创建的术语或自己术语库中的术语"
            ),
        },
        "CREATE_PROJECT": {
            "name": lazy_gettext("创建项目"),
            "intro": lazy_gettext("在团队内创建项目"),
        },
        "CREATE_PROJECT_SET": {
            "name": lazy_gettext("创建项目集"),
            "intro": lazy_gettext("在团队内创建项目集"),
        },
        "CHANGE_PROJECT_SET": {
            "name": lazy_gettext("设置项目集"),
            "intro": lazy_gettext("修改团队内项目集的设置"),
        },
        "DELETE_PROJECT_SET": {
            "name": lazy_gettext("删除项目集"),
            "intro": lazy_gettext("删除团队内的项目集"),
        },
        "USE_OCR_QUOTA": {
            "name": lazy_gettext("使用自动标记额度"),
            "intro": lazy_gettext("可以使用团队的自动标记额度"),
        },
        "USE_MT_QUOTA": {
            "name": lazy_gettext("使用机器翻译额度"),
            "intro": lazy_gettext("可以使用团队的机器翻译额度"),
        },
        "INSIGHT": {
            "name": lazy_gettext("查看项目统计"),
            "intro": lazy_gettext("可以查看团队项目统计"),
        },
    }


class TeamRole(RoleMixin, Document):
    permission_cls = TeamPermission
    group = ReferenceField("Team", db_field="g")
    system_role_data = [
        {
            "name": gettext("创建人"),
            "permissions": [
                TeamPermission.ACCESS,
                TeamPermission.DELETE,
                TeamPermission.CHANGE,
                TeamPermission.CREATE_ROLE,
                TeamPermission.DELETE_ROLE,
                TeamPermission.AUTO_BECOME_PROJECT_ADMIN,
                TeamPermission.CHECK_USER,
                TeamPermission.INVITE_USER,
                TeamPermission.DELETE_USER,
                TeamPermission.CHANGE_USER_ROLE,
                TeamPermission.CHANGE_USER_REMARK,
                TeamPermission.CREATE_TERM_BANK,
                TeamPermission.ACCESS_TERM_BANK,
                TeamPermission.CHANGE_TERM_BANK,
                TeamPermission.DELETE_TERM_BANK,
                TeamPermission.CREATE_TERM,
                TeamPermission.CHANGE_TERM,
                TeamPermission.DELETE_TERM,
                TeamPermission.CREATE_PROJECT,
                TeamPermission.CREATE_PROJECT_SET,
                TeamPermission.CHANGE_PROJECT_SET,
                TeamPermission.DELETE_PROJECT_SET,
                TeamPermission.USE_OCR_QUOTA,
                TeamPermission.USE_MT_QUOTA,
                TeamPermission.INSIGHT,
            ],
            "level": 500,
            "system_code": "creator",
        },
        {
            "name": gettext("管理员"),
            "permissions": [
                TeamPermission.ACCESS,
                TeamPermission.CHANGE,
                TeamPermission.CREATE_ROLE,
                TeamPermission.DELETE_ROLE,
                TeamPermission.AUTO_BECOME_PROJECT_ADMIN,
                TeamPermission.CHECK_USER,
                TeamPermission.INVITE_USER,
                TeamPermission.DELETE_USER,
                TeamPermission.CHANGE_USER_ROLE,
                TeamPermission.CHANGE_USER_REMARK,
                TeamPermission.CREATE_TERM_BANK,
                TeamPermission.ACCESS_TERM_BANK,
                TeamPermission.CHANGE_TERM_BANK,
                TeamPermission.DELETE_TERM_BANK,
                TeamPermission.CREATE_TERM,
                TeamPermission.CHANGE_TERM,
                TeamPermission.DELETE_TERM,
                TeamPermission.CREATE_PROJECT,
                TeamPermission.CREATE_PROJECT_SET,
                TeamPermission.CHANGE_PROJECT_SET,
                TeamPermission.DELETE_PROJECT_SET,
                TeamPermission.USE_OCR_QUOTA,
                TeamPermission.USE_MT_QUOTA,
                TeamPermission.INSIGHT,
            ],
            "level": 400,
            "system_code": "admin",
        },
        {
            "name": gettext("资深成员"),
            "permissions": [
                TeamPermission.ACCESS,
                TeamPermission.CREATE_TERM_BANK,
                TeamPermission.ACCESS_TERM_BANK,
                TeamPermission.CHANGE_TERM_BANK,
                TeamPermission.DELETE_TERM_BANK,
                TeamPermission.CREATE_TERM,
                TeamPermission.CHANGE_TERM,
                TeamPermission.DELETE_TERM,
                TeamPermission.CREATE_PROJECT,
                TeamPermission.CREATE_PROJECT_SET,
                TeamPermission.CHANGE_PROJECT_SET,
                TeamPermission.DELETE_PROJECT_SET,
                TeamPermission.USE_OCR_QUOTA,
                TeamPermission.USE_MT_QUOTA,
            ],
            "level": 300,
            "system_code": "senior",
        },
        {
            "name": gettext("成员"),
            "permissions": [
                TeamPermission.ACCESS,
                TeamPermission.CREATE_TERM_BANK,
                TeamPermission.ACCESS_TERM_BANK,
                TeamPermission.CHANGE_TERM_BANK,
                TeamPermission.DELETE_TERM_BANK,
                TeamPermission.CREATE_TERM,
                TeamPermission.CHANGE_TERM,
                TeamPermission.DELETE_TERM,
                TeamPermission.CREATE_PROJECT,
                TeamPermission.CREATE_PROJECT_SET,
                TeamPermission.CHANGE_PROJECT_SET,
                TeamPermission.DELETE_PROJECT_SET,
            ],
            "level": 200,
            "system_code": "member",
        },
        {
            "name": gettext("见习成员"),
            "permissions": [TeamPermission.ACCESS],
            "level": 100,
            "system_code": "beginner",
        },
    ]

    def convert_to_project_role(self):
        # 如果有AUTO_BECOME_PROJECT_ADMIN权限，则返回项目管理员权限
        if self.has_permission(self.permission_cls.AUTO_BECOME_PROJECT_ADMIN):
            return ProjectRole.by_system_code("admin")


class Team(GroupMixin, Document):
    name = StringField(db_field="n", unique=True)  # 名称
    _avatar = StringField(db_field="a", default="")  # 头像
    intro = StringField(db_field="i", default="")  # 团队介绍
    default_role_system_code = "beginner"
    default_role = ReferenceField("TeamRole", db_field="dr", reverse_delete_rule=DENY)
    max_user = IntField(db_field="u", required=True, default=100000)  # 人数限制
    # OCR限额
    ocr_quota_month = IntField(db_field="om", default=0)  # 每月限额
    ocr_quota_used = IntField(db_field="ou", default=0)  # 当月已用限额，每月1号0点清零
    ocr_quota_google_used = IntField(db_field="og", default=0)  # 谷歌 VISION 解析的张数
    ocr_quota_with_end_time = IntField(db_field="ot", default=0)  # （弃用）有时限的限额
    ocr_quota_end_time = DateTimeField(db_field="ol")  # （弃用）
    # 各种相关类
    role_cls = TeamRole
    permission_cls = TeamPermission
    allow_apply_type_cls = AllowApplyType

    @classmethod
    def create(
        cls,
        name,
        creator=None,
        default_role=None,
        allow_apply_type=None,
        application_check_type=None,
        intro="",
    ):
        """创建一个团体"""
        # 建立团队
        team = cls(name=name)
        # 设置默认角色
        if default_role:
            team.default_role = default_role
        else:
            team.default_role = cls.default_system_role()
        # 设置其他选项
        if allow_apply_type:
            team.allow_apply_type = allow_apply_type
        if application_check_type:
            team.application_check_type = application_check_type
        team.intro = intro
        team.save()
        # 添加默认项目集
        team.create_default_project_set()
        # 添加创建人
        if creator:
            creator.join(team, role=cls.role_cls.by_system_code("creator"))
        return team

    def clear(self):
        """清理删除团队"""
        for project in self.projects():
            project.clear()
        self.delete()

    @property
    def avatar(self):
        # 没有设置头像时返回默认团队头像
        if self._avatar:
            return oss.sign_url(
                current_app.config["OSS_TEAM_AVATAR_PREFIX"], self._avatar
            )
        return current_app.config.get("DEFAULT_TEAM_AVATAR", None)

    @avatar.setter
    def avatar(self, value):
        self._avatar = value

    def has_avatar(self):
        return bool(self._avatar)

    @property
    def relation_cls(self):
        return TeamUserRelation

    @classmethod
    def verify_new_name(cls, name):
        """
        验证名称是否符合要求

        :param name:
        :return:
        """
        # 检测长度
        if not 2 <= len(name) <= 18:
            raise TeamNameLengthError
        # 检测合法性
        if re.match(TEAM_NAME_REGEX, name) is None:
            raise TeamNameRegexError
        # 检测唯一性
        if cls.objects(name__iexact=name).count() > 0:
            raise TeamNameRegisteredError

    def term_banks(self, skip=None, limit=None, order_by=None, word=None):
        """返回团队所有术语库"""
        banks = TermBank.objects(team=self)
        banks = mongo_order(banks, order_by, ["-edit_time"])
        banks = mongo_slice(banks, skip, limit)
        if word:
            banks = banks.filter(name__icontains=word)
        return banks

    def create_default_project_set(self):
        """创建默认的“未分组”项目集"""
        # 检查是否已有默认项目集
        project_set = ProjectSet.objects(team=self, default=True).first()
        # 没有则创建
        if project_set is None:
            project_set = ProjectSet.create("default", self, default=True)
        return project_set

    @property
    def default_project_set(self) -> ProjectSet:
        return ProjectSet.objects(team=self, default=True).first()

    def project_sets(
        self,
        skip: int = None,
        limit: int = None,
        order_by: list = None,
        word: str = None,
    ):
        """返回团队所有项目集"""
        sets = ProjectSet.objects(team=self)
        if word:
            sets = sets.filter(name__icontains=word)
        sets = mongo_order(sets, order_by, ["-default", "-edit_time"])
        sets = mongo_slice(sets, skip, limit)
        return sets

    def projects(
        self,
        skip=None,
        limit=None,
        project_set=None,
        status=None,
        order_by: list = None,
        word=None,
    ):
        """
        获取团队项目

        :param skip: 跳过的数量
        :param limit: 限制的数量
        :param project_set: 限制在某个项目集中
        :param status: 查询何种进度的项目
        :param order_by: 排序
        :param word: 名称模糊查询
        :return:
        """
        projects = Project.objects(team=self)
        # 限制在某个项目集中
        if project_set:
            projects = projects.filter(project_set=project_set)
        # 模糊查找名称
        if word:
            projects = projects.filter(name__icontains=word)
        # 查询何种进度的项目，空列表则忽略
        if isinstance(status, list) and len(status) > 0:
            projects = projects.filter(status__in=status)
        elif isinstance(status, int):
            projects = projects.filter(status=status)
        # 排序处理
        projects = mongo_order(projects, order_by, ["-edit_time"])
        # 分页处理
        projects = mongo_slice(projects, skip, limit)
        return projects

    @classmethod
    def by_id(cls, id):
        team = cls.objects(id=id).first()
        if team is None:
            raise TeamNotExistError()
        return team

    @property
    def ocr_quota_left(self):
        """剩余的OCR配额"""
        ocr_quota_total = self.ocr_quota_month
        if (
            self.ocr_quota_end_time
            and self.ocr_quota_end_time >= datetime.datetime.utcnow()
        ):
            ocr_quota_total += self.ocr_quota_with_end_time
        return ocr_quota_total - self.ocr_quota_used

    def init_ocr_quota(self):
        """初始化OCR配额"""
        self.ocr_quota_used = 0
        self.save()

    def to_api(self, user=None):
        """
        @apiDefine TeamPublicInfoModel
        @apiSuccess {String} group_type 团体类型
        @apiSuccess {String} id ID
        @apiSuccess {String} name 名称
        @apiSuccess {String} intro 介绍
        @apiSuccess {String} avatar 头像地址
        @apiSuccess {String} has_avatar 是否设置头像，true时avatar则为默认头像地址
        @apiSuccess {Number} max_user 最大用户数
        @apiSuccess {String} default_role 默认角色 ID
        @apiSuccess {String} allow_apply_type 允许申请的类型
        @apiSuccess {String} application_check_type 如何处理申请
        @apiSuccess {String} is_need_check_application 是否需要确认申请
        @apiSuccess {String} role 用户在团体中的角色
        @apiSuccess {String} create_time 创建时间
        @apiSuccess {String} edit_time 修改时间
        """
        # 如果给了 role 则获取用户相关信息（角色等）
        role = None
        if user:
            role = user.get_role(self)
            if role:
                role = role.to_api()
        return {
            "group_type": "team",
            "id": str(self.id),
            "name": self.name,
            "intro": self.intro,
            "avatar": self.avatar,
            "has_avatar": bool(self._avatar),
            "max_user": self.max_user,
            "user_count": self.user_count,
            "default_role": str(self.default_role.id),
            "allow_apply_type": self.allow_apply_type,
            "application_check_type": self.application_check_type,
            "is_need_check_application": self.is_need_check_application(),
            "role": role,
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
            "ocr_quota_month": self.ocr_quota_month,
            "ocr_quota_used": self.ocr_quota_used,
        }


Team.register_delete_rule(TeamRole, "group", CASCADE)
Team.register_delete_rule(Application, "group", CASCADE)
Team.register_delete_rule(Invitation, "group", CASCADE)
Team.register_delete_rule(Project, "team", DENY)
Team.register_delete_rule(ProjectSet, "team", CASCADE)
Team.register_delete_rule(TermBank, "team", CASCADE)


class TeamUserRelation(RelationMixin, Document):
    user = ReferenceField("User", db_field="u", required=True)
    group = ReferenceField(
        "Team", db_field="g", required=True, reverse_delete_rule=CASCADE
    )
    role = ReferenceField("TeamRole", db_field="r", required=True)
