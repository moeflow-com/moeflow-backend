import logging
from typing import Optional
from flask import g, request
from app.constants.locale import Locale
import flask_babel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_request_locale() -> Optional[str]:
    current_user = g.get("current_user")
    req_header = f"{request.method} {request.path}"
    if (
        current_user
        and current_user.locale
        and current_user.locale != "auto"
        and current_user.locale in Locale.ids()
    ):
        # NOTE User.locale is not used , so this won't get called
        logging.debug(
            "%s set locale=%s from user pref", req_header, current_user.locale
        )
        return current_user.locale
    # "zh" locale asssets is created from hardcoded strings
    # "en" locale are machine translated
    best_match = request.accept_languages.best_match(["zh", "en"], default="en")
    logging.debug("%s set locale=%s from req", req_header, best_match)
    return best_match


# @babel.timezoneselector
# def get_timezone():
#     # TODO 弄清 timezone 是什么东西
#     current_user = g.get('current_user')
#     if current_user:
#         if current_user.timezone:
#             return current_user.timezone


def gettext(msgid: str):
    translated = flask_babel.gettext(msgid)
    logger.debug(
        f"get_text({msgid}, locale={flask_babel.get_locale()}) -> {translated}"
    )
    return translated


def lazy_gettext(msgid: str):
    translated = flask_babel.LazyString(lambda: gettext(msgid))
    # logger.debug(f"lazy_get_text({msgid}) -> {translated}")
    return translated
