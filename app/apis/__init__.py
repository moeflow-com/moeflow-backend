"""
所有的API编写在此
"""

import logging

from flask import Blueprint, Flask

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
@apiDefine TokenHeader
@apiHeader {String} Authorization
身份验证token.

格式为 `Bearer xxx`
"""
"""
@apiDefine APIHeader
@apiHeader {String} Content-Type
数据类型

必须为 `application/json`
@apiHeader {String} [Accept-Language]
请求语言 *暂仅支持 `zh-CN`*

格式为 `<语言代号>;q=<喜好程度[0-1]>`, 多个语言使用逗号分割

示例 `zh-TW;q=0.8,zh;q=0.6`
"""
"""
@apiDefine 204
@apiSuccess (Success 204) null 响应成功，无返回值
"""


def register_apis(app: Flask):
    """
    自动注册蓝本

    :param app:
    :return:
    """
    logger.info("Register route blueprints")
    # 获取urls中所有蓝本
    from . import urls

    blueprints = [v for k, v in vars(urls).items() if isinstance(v, Blueprint)]
    for blueprint in blueprints:
        prefix = "/" if blueprint.url_prefix is None else blueprint.url_prefix
        logger.debug(" - {}: {}".format(blueprint.name, prefix))
        app.register_blueprint(blueprint)
