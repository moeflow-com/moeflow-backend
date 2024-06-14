from app import flask_app, create_app
import app.utils.logging as app_logging
import logging

# app_logging.configure_root_logger()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_logging():
    assert 1 is 1
    logger.log(0, "notset?")
    logger.debug("debug")
    logger.info("info")
    logger.warning("warn")
    logger.error("local logger %d / %d", logger.level, logger.getEffectiveLevel())
    app_logging.logger.debug("debug to global logger")
    app_logging.logger.info("info to global logger")
    app_logging.logger.warning("warn to global logger")
    app_logging.logger.error(
        "global logger %d / %d",
        app_logging.logger.level,
        app_logging.logger.getEffectiveLevel(),
    )
    root_logger = logging.getLogger("root")
    logging.error(
        "root logger %d / %d", root_logger.level, root_logger.getEffectiveLevel()
    )
    create_app()
