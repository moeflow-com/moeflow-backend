from functools import wraps
from typing import Optional

from mongoengine.errors import ValidationError

from app.exceptions import NotExistError, GroupTypeNotSupportError
from app.models.project import Project
from app.models.team import Team
from app.utils.str import to_underscore


def fetch_model(
    document: type, from_name: Optional[str] = None, to_name: Optional[str] = None
):
    """
    从url的id中获取相对应的模型对象

    :param document: 从此Document中寻找
    :param from_name: url中的变量名，默认为 小写document名 + _id (如：team_id)
    :param to_name: 返回给函数的变量名，默认为 小写document名 （如：team）
    :return:
    """
    if from_name is None:
        from_name = to_underscore(document.__name__) + "_id"
    if to_name is None:
        to_name = to_underscore(document.__name__)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            id = kwargs.pop(from_name)
            try:
                obj = document.objects(id=id).first()
            except ValidationError:
                obj = None
            if obj is None:
                raise NotExistError(document.__name__)
            return func(*args, **kwargs, **{to_name: obj})

        return wrapper

    return decorator


def fetch_group(func):
    """
    从url中，根据group_type和group_id获取group对象
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        group_type = kwargs.pop("group_type")
        group_id = kwargs.pop("group_id")
        # 获取group
        if group_type == "teams":
            group = Team.objects(id=group_id).first()
        elif group_type == "projects":
            group = Project.objects(id=group_id).first()
        else:
            raise GroupTypeNotSupportError
        # 如果group不存在
        if group is None:
            raise NotExistError(group_type[:-1].capitalize())
        return func(*args, **kwargs, **{"group": group})

    return wrapper
