from functools import wraps

from flask import g, request

from app.exceptions import NeedTokenError, UserBannedError, NoPermissionError
from app.models.user import User


def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token is None:
            raise NeedTokenError
        current_user = User.verify_token(token)
        # 检查用户状态
        if current_user.banned:
            raise UserBannedError
        # 赋值到g对象
        g.current_user = current_user
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token is None:
            raise NeedTokenError
        current_user = User.verify_token(token)
        # 检查用户状态
        if not current_user.admin_can():
            raise NoPermissionError
        # 赋值到g对象
        g.current_user = current_user
        return func(*args, **kwargs)

    return wrapper
