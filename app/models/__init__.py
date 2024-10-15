"""
模型
"""

import logging
from mongoengine import connect

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def connect_db(config):
    logger.info("Connect mongodb")
    uri = config["DB_URI"]
    logger.debug(" - $DB_URI: {}".format(uri))
    if config.get("TESTING"):
        import mongomock

        return connect(host=uri, mongo_client_class=mongomock.MongoClient)

    return connect(host=uri)


# TODO 为所有模型添加索引
