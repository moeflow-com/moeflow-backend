from flask import g, request
from app.constants.locale import Locale


def get_locale() -> str:
    current_user = g.get("current_user")
    if (
        current_user
        and current_user.locale
        and current_user.locale != "auto"
        and current_user.locale in Locale.ids()
    ):
        return current_user.locale
    return request.accept_languages.best_match(["zh_CN", "zh_TW", "zh", "en_US", "en"])


# @babel.timezoneselector
# def get_timezone():
#     # TODO 弄清 timezone 是什么东西
#     current_user = g.get('current_user')
#     if current_user:
#         if current_user.timezone:
#             return current_user.timezone
