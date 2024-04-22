"""
模型
"""

from mongoengine import connect

from app.utils.logging import logger


def connect_db(config):
    logger.info("-" * 50)
    logger.info("连接 mongodb:")
    uri = config["DB_URI"]
    logger.info(" - uri: {}".format(uri))
    return connect(host=uri)


# TODO 为所有模型添加索引
