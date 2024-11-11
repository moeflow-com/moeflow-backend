"""
权限,角色,团体,关系Minix类
并集成加入流程功能
"""

import datetime
import logging
from app.exceptions import UserNotExistError, CreatorCanNotLeaveError

from flask_babel import gettext, lazy_gettext
from mongoengine import (
    BooleanField,
    DateTimeField,
    IntField,
    ListField,
    Q,
    StringField,
    Document,
)

from app.exceptions import (
    AllowApplyTypeNotExistError,
    ApplicationCheckTypeNotExistError,
    NoPermissionError,
    PermissionNotExistError,
    RoleNotExistError,
)
from app.models.application import Application
from app.models.invitation import Invitation
from app.constants.base import IntType
from app.constants.role import RoleType
from app.utils.mongo import mongo_order, mongo_slice
from typing import List, Any, Type

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)


class AllowApplyType(IntType):
    """
    允许谁申请加入
    """

    NONE = 1
    ALL = 2

    details = {
        "NONE": {
            "name": lazy_gettext("关闭申请加入"),
            "intro": lazy_gettext("只能通过邀请新增成员"),
        },
        "ALL": {
            "name": lazy_gettext("所有人"),
            "intro": lazy_gettext("所以用户都可以申请加入"),
        },
    }


class ApplicationCheckType(IntType):
    """
    如何处理申请
    """

    NO_NEED_CHECK = 1
    ADMIN_CHECK = 2

    details = {
        "NO_NEED_CHECK": {
            "name": lazy_gettext("无需审核"),
            "intro": lazy_gettext("用户申请后直接加入"),
        },
        "ADMIN_CHECK": {
            "name": lazy_gettext("管理员审核"),
            "intro": lazy_gettext("管理员同意申请后加入"),
        },
    }


class PermissionMixin(IntType):
    """
    供权限类使用，未来可添加公用的方法
    """

    # 基础权限，为0 - 99
    ACCESS = 1
    DELETE = 5
    CHANGE = 10
    CREATE_ROLE = 15
    DELETE_ROLE = 20
    # 加入流程权限，为 100 - 199
    CHECK_USER = 101
    INVITE_USER = 105
    DELETE_USER = 110
    CHANGE_USER_ROLE = 115
    CHANGE_USER_REMARK = 120
    # 自定义权限为 1000 以上

    details = {
        "ACCESS": {"name": lazy_gettext("访问")},
        "DELETE": {"name": lazy_gettext("解散")},
        "CHANGE": {"name": lazy_gettext("修改设置")},
        "CREATE_ROLE": {"name": lazy_gettext("新建角色")},
        "DELETE_ROLE": {"name": lazy_gettext("删除角色")},
        "CHECK_USER": {"name": lazy_gettext("审核用户加入申请")},
        "INVITE_USER": {
            "name": lazy_gettext("邀请用户"),
            "intro": lazy_gettext("邀请时仅可设置比自己角色等级低的用户"),
        },
        "DELETE_USER": {
            "name": lazy_gettext("删除用户"),
            "intro": lazy_gettext("仅可删除比自己角色等级低的用户"),
        },
        "CHANGE_USER_ROLE": {
            "name": lazy_gettext("修改用户角色"),
            "intro": lazy_gettext("仅可修改比自己角色等级低的角色"),
        },
        "CHANGE_USER_REMARK": {"name": lazy_gettext("修改用户备注")},
    }


class RoleMixin:
    """
    继承类需要指定permission_cls，以供解析写入数据库
    """

    _name: str = StringField(db_field="m_n", required=True)
    level: int = IntField(db_field="m_l", required=True)
    intro: str = StringField(db_field="m_i", default="")
    permissions: List[int] = ListField(IntField(), db_field="m_p", default=list)
    system: bool = BooleanField(db_field="m_s", required=True, default=False)
    system_code: str = StringField(
        db_field="m_o"
    )  # 用于代码中调用此角色，用户创建的没有
    create_time: datetime = DateTimeField(
        db_field="m_c", default=datetime.datetime.utcnow
    )
    system_role_data: List[dict] = []

    def clean(self):
        # ==处理permission==
        # 如果是权限的子集
        if set(self.permissions) <= set(self.permission_cls.ids()):
            # 去重并赋值给permission
            self.permissions = list(set(self.permissions))
        else:
            raise PermissionNotExistError

    @property
    def permission_cls(self) -> PermissionMixin:
        """需要指定所使用的权限类"""
        raise NotImplementedError

    @property
    def name(self):
        # 系统角色返回翻译的名字
        if self.system:
            return gettext(self._name)
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def has_permission(self, permission: int):
        """是否有权限"""
        if permission in self.permissions:
            return True
        else:
            return False

    @classmethod
    def init_system_roles(cls: Type[Document]):
        """初始化系统角色"""
        logger.info("-" * 50)
        if cls.objects().count() == 0:
            for role in cls.system_role_data:
                exist_role = cls.objects(system_code=role["system_code"]).first()
                if exist_role is None:
                    logger.info(f' - 创建 {role["name"]}')
                    cls(
                        _name=role["name"],
                        permissions=role["permissions"],
                        level=role["level"],
                        system=True,
                        system_code=role["system_code"],
                        intro=role.get("intro", ""),
                    ).save()
            logger.info(f"Populated {cls._class_name} with default roles")
        else:
            logger.info(f"{cls._class_name} already populated")

    @classmethod
    def system_roles(cls: Type[Document], without_creator=False):
        query: dict[str, Any] = {"system": True}
        if without_creator:
            query["system_code__ne"] = "creator"
        roles = cls.objects(**query)
        return roles

    @classmethod
    def by_system_code(cls: Type[Document], code):
        """通过system_code查询角色"""
        role = cls.objects(system_code=code).first()
        if role is None:
            raise RoleNotExistError
        return role

    @classmethod
    def by_id(cls: Type[Document], id):
        """通过system_code查询角色"""
        role = cls.objects(id=id).first()
        if role is None:
            raise RoleNotExistError
        return role

    def to_api(self: Document):
        name = gettext(self.name)
        logger.debug('RoleMixin.to_api: name="%s" %s', self.name, name)
        return {
            "id": str(self.id),
            "name": gettext(self.name),
            "level": self.level,
            "system": self.system,
            "system_code": self.system_code,
            "permissions": self.permission_cls.to_api(ids=self.permissions),
            "create_time": self.create_time.isoformat(),
        }


class RelationMixin:
    meta = {"indexes": ["user", "group", ("user", "group"), ("user", "role")]}

    create_time = DateTimeField(db_field="m_c", default=datetime.datetime.utcnow)
    tags = ListField(StringField(), db_field="m_t", default=list)  # 用户标签

    def clean(self):
        # ==处理role==
        # 检测设定的role是否是系统role或者相关group的role
        if self.role not in self.group.roles():
            raise RoleNotExistError(self.role.name)


class GroupMixin:
    """
    继承类需要定义
    relation_cls，以供取得关系表
    role_cls，以供取得默认角色
    """

    allow_apply_type = IntField(
        db_field="m_a", default=AllowApplyType.NONE, required=True
    )  # 允许申请加入的类型
    application_check_type = IntField(
        db_field="m_t", default=ApplicationCheckType.ADMIN_CHECK, required=True
    )  # 审核模式
    max_user = IntField(db_field="m_u", required=True, default=100000)
    user_count = IntField(db_field="m_uc", required=True, default=0)  # 当前人数缓存
    create_time = DateTimeField(db_field="m_c", default=datetime.datetime.utcnow)
    edit_time = DateTimeField(db_field="m_e", default=datetime.datetime.utcnow)
    application_check_type_cls = ApplicationCheckType
    allow_apply_type_cls = AllowApplyType

    def clean(self):
        # ==处理application_check_type==
        if self.application_check_type not in self.application_check_type_cls.ids():
            raise ApplicationCheckTypeNotExistError(self.application_check_type)
        # ==处理allow_apply_type==
        if self.allow_apply_type not in self.allow_apply_type_cls.ids():
            raise AllowApplyTypeNotExistError(self.allow_apply_type)

    def create_role(self: Document, name, level, permissions, operator=None, intro=""):
        """
        添加自定义角色

        :param name: 名称
        :param level: 等级
        :param permissions: 拥有的权限
        :param operator: 操作人，如果提供了操作人，则会根据操作人的角色，限制新建立的角色的level和permission
        :param intro: 介绍
        :return:
        """
        # 建立的角色限制于操作人自身的角色
        if operator:
            operator_role = operator.get_role(self)
            if level >= operator_role.level:
                raise NoPermissionError(gettext("角色等级不能大于等于自己的角色等级"))
            if not (set(permissions) <= set(operator_role.permissions)):
                raise NoPermissionError(gettext("角色权限不能多于自己的角色权限"))
        permissions = list(set(permissions))
        role = self.role_cls(
            _name=name,
            level=level,
            intro=intro,
            group=self,
            permissions=permissions,
        ).save()
        return role

    def edit_role(
        self: Document, id, name, level, permissions, operator=None, intro=""
    ):
        """
        修改角色

        :param id: id
        :param name: 名称
        :param level: 等级
        :param permissions: 拥有的权限
        :param operator: 操作人，如果提供了操作人，则会根据操作人的角色，限制新建立的角色的level和permission
        :param intro: 介绍
        :return:
        """
        role = self.roles(type=RoleType.CUSTOM).filter(id=id).first()
        # 没有role
        if role is None:
            raise RoleNotExistError
        # 系统角色不能修改
        if role.system:
            raise NoPermissionError(gettext("不能修改系统角色"))
        # 建立的角色限制于操作人自身的角色
        if operator:
            operator_role = operator.get_role(self)
            if level >= operator_role.level:
                raise NoPermissionError(gettext("角色等级不能大于等于自己的角色等级"))
            if not (set(permissions) <= set(operator_role.permissions)):
                raise NoPermissionError(gettext("角色权限不能多于自己的角色权限"))
        # 修改role的各种信息
        role.name = name
        role.level = level
        role.permissions = permissions
        role.intro = intro
        role.save()

    def delete_role(self: Document, id: str):
        role = self.roles(type=RoleType.CUSTOM).filter(id=id).first()
        # 没有role
        if role is None:
            raise RoleNotExistError
        # 系统角色不能删除
        if role.system:
            raise NoPermissionError(gettext("不能删除系统角色"))
        # 处理default_role，如果有关联的话，将系统默认角色设置为默认角色
        if self.default_role == role:
            self.default_role = self.default_system_role()
            self.save()
        # 处理使用这个role的角色
        self.relation_cls.objects(group=self, role=role).update(
            role=self.default_system_role()
        )
        # 删除role
        role.delete()

    def is_full(self):
        """团体人数是否已满"""
        if self.users().count() >= self.max_user:
            return True
        return False

    @property
    def default_role_system_code(self) -> str:
        """默认的角色的system code"""
        raise NotImplementedError

    @classmethod
    def default_system_role(cls):
        """返回系统默认角色，供设置初始默认角色和还原默认角色使用"""
        return cls.role_cls.by_system_code(cls.default_role_system_code)

    @property
    def relation_cls(self) -> RelationMixin:
        """关联的关系类"""
        raise NotImplementedError

    @property
    def role_cls(self) -> RoleMixin:
        """关联的角色类"""
        raise NotImplementedError

    def is_allow_apply(self, user) -> bool:
        """
        是否允许此用户申请加入，当不能加入时必须抛出无权限异常
        如果要复写此方法需要在最后一行
        return super().is_allow_apply(user)
        """
        # 项目允许所有人申请加入
        if self.allow_apply_type == AllowApplyType.ALL:
            return True
        # 项目不允许申请加入
        if self.allow_apply_type == AllowApplyType.NONE:
            raise NoPermissionError(gettext("此项目/团队不允许申请加入"))
        raise NoPermissionError(gettext("此项目/团队不允许申请加入") + "(1)")

    def is_need_check_application(self) -> bool:
        """是否需要确认申请"""
        if self.application_check_type == ApplicationCheckType.NO_NEED_CHECK:
            return False
        return True

    @property
    def permission_cls(self):
        """关联的权限类"""
        return self.role_cls.permission_cls

    @property
    def group_type(self):
        """
        返回一个全小写的类名
        Team -> team
        Project -> project
        """
        return self._class_name.lower()

    def to_api(self):
        """
        目标团体的基本信息,用于在界面显示头像等,需要包含id以供进一步查询

        :return: dict 团队基本信息
        """
        raise NotImplementedError("Need implement this method to show group :to_api()")

    def users(self, role=None, skip: int = None, limit: int = None, word: str = None):
        """
        获取所有用户

        :param role: 用户的角色，可以是一个列表
        :param skip: 跳过的数量
        :param limit: 限制的数量
        :param word: 模糊搜索词
        :return:
        """
        from app.models.user import User

        # 搜索相关的用户
        relational_users = (
            self.relation_cls.objects(group=self).scalar("user").no_dereference()
        )
        if role:
            if isinstance(role, list):
                relational_users = relational_users.filter(role__in=role)
            else:
                relational_users = relational_users.filter(role=role)
        # 进一步筛选
        users = User.objects(id__in=[u.id for u in relational_users])
        # 模糊搜索词
        if word:
            users = users.filter(name__icontains=word)
        # 处理分页
        users = mongo_slice(users, skip, limit)
        return users

    def users_by_permission(self, permission):
        """
        通过权限获取所有相关的用户
        """
        roles = self.roles()
        roles_by_permission = []
        for role in roles:
            if permission in role.permissions:
                roles_by_permission.append(role)
        return self.users(role=roles_by_permission)

    def delete_uesr(self, user, operator=None):
        user_role = user.get_role(self)
        # 检查被删除用户是否存在于团队
        if user_role is None:
            raise UserNotExistError(gettext("用户不存在于团队"), replace=True)
        # 创建者不能删除
        if user_role.system_code == "creator":
            raise CreatorCanNotLeaveError
        # 有操作人则检测权限
        if operator:
            # 如果是自己，直接删除
            if operator == user:
                user.leave(self)
                self.reload()
                return {"message": gettext("退出成功"), "group": self.to_api(user=user)}
            operator_role = operator.get_role(self)
            # 检查当前用户是否有删除权限
            if not operator.can(self, self.permission_cls.DELETE_USER):
                raise NoPermissionError(gettext("您没有删除用户权限"))
            # 检查当前用户和被删除用户等级
            if user_role.level >= operator_role.level:
                raise NoPermissionError(gettext("只能删除角色等级比您低的用户"))
        user.leave(self)
        return {"message": gettext("删除成功")}

    def change_user_role(self, user, role, operator=None):
        """修改用户角色"""
        # 如果是字符串，则获取 Role 实例
        if isinstance(role, str):
            role = self.role_cls.by_id(role)
            # 没有角色或角色不在团体内则报错
            if role is None or (role.group is not None and role.group != self):
                raise RoleNotExistError
        # 检查 user 是否在团队内
        user_role = user.get_role(self)
        if user_role is None:
            raise UserNotExistError
        # 有操作人则检查权限
        if operator:
            # 不能修改自己的角色
            if operator == user:
                raise NoPermissionError(gettext("您不能修改自己的角色"))
            # 是否有修改用户角色的权限
            if not operator.can(self, self.permission_cls.CHANGE_USER_ROLE):
                raise NoPermissionError(gettext("您没有修改用户角色权限"))
            operator_role = operator.get_role(self)
            # 检查操作人和被设置用户的等级
            if user_role.level >= operator_role.level:
                raise NoPermissionError(gettext("只能为比您角色等级低的用户设置角色"))
            # 检查操作人和将要设置角色的等级
            if role.level >= operator_role.level:
                raise NoPermissionError(gettext("只能为用户设置比您角色等级低的角色"))
        # 设置角色
        user.set_role(self, role)
        return role

    def invitations(self, user=None, status=None, skip=None, limit=None):
        """获取团体发出的所有的邀请"""
        invitations = Invitation.get(
            group=self, user=user, status=status, skip=skip, limit=limit
        )
        return invitations

    def applications(self, user=None, status=None, skip=None, limit=None):
        """获取团体收到的所有的申请"""
        applications = Application.get(
            group=self, user=user, status=status, skip=skip, limit=limit
        )
        return applications

    @property
    def default_role(self):
        return self._default_role

    @default_role.setter
    def default_role(self, role):
        """通过role_id设置默认角色"""
        # 默认角色不能设置为创建者
        if role.system_code == "creator":
            NoPermissionError(gettext("默认角色不能设置为创建者"))
        # 角色不是这个团体的
        if role not in self.roles(without_creator=True):
            raise RoleNotExistError
        self._default_role = role

    def roles(
        self: Document,
        type=RoleType.ALL,
        without_creator=False,
        skip=None,
        limit=None,
        order_by=None,
    ) -> List[RoleMixin]:
        """
        获得所有角色

        :param type: 获取角色的类型，可选：
            all：所有角色
            system：系统角色
            custom：自定义角色（without_creator对此类型没有作用）
        :param without_creator: 系统角色是否排除创建者，默认包含
        :return:
        """
        # 团体查询参数
        query = {}
        if without_creator:
            query["system_code__ne"] = "creator"
        # 根据不同类型查询
        if type == RoleType.CUSTOM:
            roles = self.role_cls.objects(group=self)
        elif type == RoleType.SYSTEM:
            roles = self.role_cls.objects(system=True).filter(**query)
        elif type == RoleType.ALL:
            roles = self.role_cls.objects(Q(group=self) | Q(system=True)).filter(
                **query
            )
        else:
            raise ValueError("roles的type只可为RoleType的常量")
        # 处理排序
        roles = mongo_order(roles, order_by, ["system"])
        # 处理分页
        roles = mongo_slice(roles, skip, limit)
        return roles
