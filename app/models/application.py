from app.exceptions import ApplicationFinishedError
from app.utils.mongo import mongo_slice
from flask_babel import gettext
from mongoengine import (
    Document,
    GenericReferenceField,
    IntField,
    ReferenceField,
    StringField,
    ObjectIdField,
)
from mongoengine.fields import ListField


class ApplicationStatus:
    PENDING = 1
    ALLOW = 2
    DENY = 3


class Application(Document):
    user = ReferenceField("User", db_field="u", required=True)  # 申请人
    operator = ReferenceField("User", db_field="o")  # 处理人
    group = GenericReferenceField(
        choices=["Team", "Project"], db_field="g", required=True
    )
    status: int = IntField(
        required=True, default=ApplicationStatus.PENDING, db_field="s"
    )
    message: str = StringField(required=True, default="", db_field="m")
    # 申请当时可以处理申请的用户，用于用户查询自己可以处理的申请
    user_ids_can_check_user = ListField(ObjectIdField(), db_field="uc", default=list)

    @classmethod
    def create(cls, /, *, user, group, message):
        user_ids_can_check_user = [
            user.id
            for user in group.users_by_permission(group.permission_cls.CHECK_USER)
        ]
        application = Application(
            user=user,
            group=group,
            message=message,
            user_ids_can_check_user=user_ids_can_check_user,
        ).save()
        return application

    @classmethod
    def get(
        cls,
        user=None,
        group=None,
        status=None,
        skip=None,
        limit=None,
        related_user_id=None,
    ):
        applications = cls.objects()
        if user:
            applications = applications.filter(user=user)
        if group:
            applications = applications.filter(group=group)
        if status:
            # 如果是[1]这种只有一个参数的,则提取数组第一个元素，不使用in查询
            if isinstance(status, list) and len(status) == 1:
                status = status[0]
            # 数组使用in查询
            if isinstance(status, list):
                applications = applications.filter(status__in=status)
            else:
                applications = applications.filter(status=status)
        if related_user_id:
            applications = applications.filter(user_ids_can_check_user=related_user_id)
        # 排序
        applications = applications.order_by("status", "-id")
        # 处理分页
        applications = mongo_slice(applications, skip, limit)
        return applications

    @property
    def create_time(self):
        return self.id.generation_time

    def can_change_status(self):
        """检查申请是否可转变状态"""
        if self.status == ApplicationStatus.DENY:
            raise ApplicationFinishedError(gettext("已被他人拒绝"))
        if self.status == ApplicationStatus.ALLOW:
            raise ApplicationFinishedError(gettext("已被他人允许"))

    def allow(self, operator, role=None):
        self.can_change_status()
        # 提供role的话则设置为此角色
        # 用于已有申请,管理员又通过接口进行邀请,并设置了角色,这时候就用这个角色加入用户
        self.user.join(self.group, role)
        self.status = ApplicationStatus.ALLOW
        self.operator = operator
        self.save()

    def deny(self, operator):
        self.can_change_status()
        self.status = ApplicationStatus.DENY
        self.operator = operator
        self.save()

    def to_api(self, /, *, user=None):
        """
        @apiDefine ApplicationInfoModel
        @apiSuccess {String} id ID
        @apiSuccess {Object} user 用户公共信息
        @apiSuccess {Object} user_role 用户在团体中的角色
        @apiSuccess {Object} group 团体
        @apiSuccess {String} group_type 目标类型,有team,project
        @apiSuccess {Object} group_roles 团队系统角色
        @apiSuccess {Object} operator 操作人
        @apiSuccess {String} create_time 创建时间
        @apiSuccess {Number} status 状态
        """
        data = {
            "id": str(self.id),
            "user": self.user.to_api(),
            "user_role": None,
            "group": self.group.to_api(user=user),
            "group_type": self.group.group_type,
            # TODO: 当实现自定义角色时，group_roles 需要同时返回所有自定义角色
            "group_roles": [
                role.to_api()
                for role in self.group.role_cls.system_roles(without_creator=True)
            ],
            "operator": self.operator.to_api() if self.operator else None,
            "create_time": self.create_time.isoformat(),
            "status": self.status,
            "message": self.message,
        }
        # 同时返回用户当前角色
        if self.status == ApplicationStatus.ALLOW and self.user.get_relation(
            self.group
        ):
            data["user_role"] = self.user.get_relation(self.group).role.to_api()
        return data
