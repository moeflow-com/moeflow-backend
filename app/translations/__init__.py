import logging
from typing import Optional
from flask import g, request
from app.constants.locale import Locale

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


def get_locale() -> Optional[str]:
    current_user = g.get("current_user")
    if (
        current_user
        and current_user.locale
        and current_user.locale != "auto"
        and current_user.locale in Locale.ids()
    ):
        # NOTE User.locale is not used
        logging.debug("locale from user %s", current_user.locale)
        return current_user.locale
    # "zh" locale asssets is created from hardcoded strings
    # "en" locale are machine translated
    best_match = request.accept_languages.best_match(["zh", "en"], default="en")
    logging.debug("locale from req %s", best_match)
    return best_match


# @babel.timezoneselector
# def get_timezone():
#     # TODO 弄清 timezone 是什么东西
#     current_user = g.get('current_user')
#     if current_user:
#         if current_user.timezone:
#             return current_user.timezone
