"""
模型
"""
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from mongoengine import connect


def connect_db(config):
    logger.info("Connect mongodb")
    uri = config["DB_URI"]
    logger.debug(" - $DB_URI: {}".format(uri))
    return connect(host=uri)

# TODO 为所有模型添加索引
