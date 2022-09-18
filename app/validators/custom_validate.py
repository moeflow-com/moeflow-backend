from bson import ObjectId
from flask_babel import gettext, lazy_gettext
from marshmallow import ValidationError, validate

from app.exceptions import InvalidObjectIdError, MoeError
from app.models.team import Team
from app.models.user import User


# ####共用部分####
def object_id(id):
    """只要不能通过ObjectID解析，就报错"""
    try:
        ObjectId(id)
    except:  # noqa: E722
        raise InvalidObjectIdError


def cant_empty(value, field_name=None):
    if len(value) == 0:
        raise ValidationError(gettext("不可为空"), field_names=field_name)


def need_in(objects):
    """
    在validate列表中定义时，仅适用于不会变化的l，如type类型，
    因为此函数的objects在第一次运行validate定义后就不会变化了
    比如objects是几个用户id，可能因为数据库中id变化，导致检测是不在里面
    从而无法测试（测试时objects在运行测试时就定义了，其他测试用例会删库，重新创建id）
    这种情况推荐在 @validates_schema 中做need_in检测
    TODO: 可以支持 objects 传入函数来动态获取，就不用在 @validates_schema 中做need_in检测
    """

    def validator(value, field_name=None):
        if value not in objects:
            raise ValidationError(gettext("此项不可选"), field_names=field_name)

    return validator


def indexes_in(model=None, other_indexes: list = None):
    """
    检查indexes是否在要求之列
    """
    indexes = []
    if model and hasattr(model, "_meta") and "indexes" in model._meta:
        # 将索引转换成列表，用于比较
        indexes = [
            [index] if isinstance(index, str) else list(index)
            for index in model._meta["indexes"]
        ]
        # 将所有索引取反
        for index in indexes.copy():
            indexes.append([i[1:] if i.startswith("-") else "-" + i for i in index])
        # 获得索引的前缀子集
        for index in indexes.copy():
            for i in range(1, len(index)):
                if index[:i] not in indexes.copy():
                    indexes.append(index[:i])
    if other_indexes:
        indexes += other_indexes

    def validator(values, field_name=None):
        # 检查排序参数是否在索引中
        if values not in indexes:
            raise ValidationError(
                gettext(f"不支持使用 {values} 排序，支持：{indexes}"), field_names=field_name,
            )

    return validator


# #####用户部分#####
class UserValidate:
    signature_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )
    password_length = validate.Length(
        min=6, max=60, error=lazy_gettext("长度为{min}到{max}个字符")
    )

    @staticmethod
    def valid_new_name(name, field_name=None):
        """用户名合法"""
        try:
            User.verify_new_name(name)
        except MoeError as e:
            raise ValidationError(e.message, field_name)

    @staticmethod
    def valid_new_email(email, field_name=None):
        """邮箱合法"""
        try:
            User.verify_new_email(email)
        except MoeError as e:
            raise ValidationError(e.message, field_name)

    @staticmethod
    def exist_email(email, field_name=None):
        """必须是已经注册的邮箱"""
        user = User.get_by_email(email)
        if user is None:
            raise ValidationError(gettext("此邮箱未注册"), field_name=field_name)


# #####团队部分#####
class TeamValidate:
    intro_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )

    @staticmethod
    def valid_new_name(name, field_name=None):
        """用户名合法"""
        try:
            Team.verify_new_name(name)
        except MoeError as e:
            raise ValidationError(e.message, field_name)


# #####项目部分#####
class ProjectValidate:
    name_length = validate.Length(
        min=1, max=40, error=lazy_gettext("长度为{min}到{max}个字符")
    )
    intro_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )


# #####项目部分#####
class ProjectSetValidate:
    name_length = validate.Length(
        min=1, max=40, error=lazy_gettext("长度为{min}到{max}个字符")
    )


# #####加入流程部分#####
class JoinValidate:
    message_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )


# #####角色部分#####
class RoleValidate:
    name_length = validate.Length(
        min=1, max=20, error=lazy_gettext("长度为{min}到{max}个字符")
    )
    intro_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )

    @staticmethod
    def valid_level(level, min=0, max=500, field_name=None):
        """团队名唯一"""
        if not (min < level < max):
            raise ValidationError(
                gettext("等级需要大于{min}，小于{max}(您的等级)".format(min=min, max=max)),
                field_names=field_name,
            )


# ##### 术语库部分 #####
class TermBankValidate:
    name_length = validate.Length(
        min=1, max=40, error=lazy_gettext("长度为{min}到{max}个字符")
    )
    tip_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )


class TermValidate:
    source_length = validate.Length(
        min=1, max=40, error=lazy_gettext("长度为{min}到{max}个字符")
    )
    target_length = validate.Length(
        min=1, max=40, error=lazy_gettext("长度为{min}到{max}个字符")
    )
    tip_length = validate.Length(
        min=0, max=140, error=lazy_gettext("长度为{min}到{max}个字符")
    )
