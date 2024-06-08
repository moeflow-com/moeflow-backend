# -*- coding: utf-8 -*-
"""
from app.utils.logging import logger
使用 logger 记录即可
"""

import os
import logging
from logging.handlers import SMTPHandler
from flask import Flask
from typing import Optional

logger = logging.getLogger(__name__)
root_logger = logging.getLogger('root')


class SMTPSSLHandler(SMTPHandler):
    """使用SMTP_SSL以支持SSL"""

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            from email.message import EmailMessage
            import email.utils

            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port, timeout=self.timeout)
            msg = EmailMessage()
            msg["From"] = self.fromaddr
            msg["To"] = ",".join(self.toaddrs)
            msg["Subject"] = self.getSubject(record)
            msg["Date"] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.username:
                if self.secure is not None:
                    smtp.ehlo()
                    smtp.starttls(*self.secure)
                    smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.send_message(msg)
            smtp.quit()
        except Exception:
            self.handleError(record)


_logger_configured = False


def configure_root_logger(override: Optional[str] = None):
    global _logger_configured
    if _logger_configured:
        return
    _logger_configured = True
    logging.debug("configuring root logger %s %s", root_logger.level, root_logger.getEffectiveLevel())
    level = override or os.environ.get('LOG_LEVEL')
    if not level:
        return
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        # filename=None,
        force=True,  # why the f is this required?
        level=getattr(logging, level.upper())
    )
    logging.debug("reset log level %s", level)


def configure_logger(app):
    """
    通过app.config自动配置logger

    :param app:
    :return:
    """
    if 'LOG_LEVEL' in os.environ:
        configure_root_logger()
        return
    if _logger_configured:
        return
    logger.setLevel(logging.DEBUG)
    # 各种格式
    stream_formatter = logging.Formatter("[%(asctime)s] (%(levelname)s) %(message)s")
    file_formatter = logging.Formatter(
        "[%(asctime)s %(pathname)s:%(lineno)d] (%(levelname)s) %(message)s"
    )

    if app.config["DEBUG"]:
        # 控制台输出
        stream_handler = logging.StreamHandler()
        # 如果测试只输出ERROR
        if app.config["TESTING"]:
            stream_handler.setLevel(logging.ERROR)
        else:
            stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(stream_formatter)  # 格式设置
        # 附加到logger
        logger.addHandler(stream_handler)
        app.logger.addHandler(stream_handler)
    else:
        # 设置了LOG_PATH则使用,否则使用默认的logs文件夹
        if app.config.get("LOG_PATH"):
            log_path = app.config.get("LOG_PATH")
            log_folder = os.path.dirname(log_path)
        else:
            log_folder = "./logs"
            log_file = "log.txt"
            log_path = os.path.join(log_folder, log_file)
        # 不存在记录文件夹自动创建
        if not os.path.isdir(log_folder):
            os.makedirs(log_folder)

        # === 控制台输出 ===
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(stream_formatter)

        # === 文件输出 ===
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(file_formatter)

        # === 邮件输出 ===
        if app.config["ENABLE_LOG_EMAIL"]:
            _enable_email_log(app)

        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
        # app.logger.addHandler(stream_handler)
        app.logger.addHandler(file_handler)


def _enable_email_log(app: Flask):
    mail_formatter = logging.Formatter(
        """
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        Message:

        %(message)s
        """
    )
    mail_handler = SMTPSSLHandler(
        (app.config["EMAIL_SMTP_HOST"], app.config["EMAIL_SMTP_PORT"]),
        app.config["EMAIL_ADDRESS"],
        app.config["EMAIL_ERROR_ADDRESS"],
        "萌翻站点发生错误",
        credentials=(
            app.config["EMAIL_ADDRESS"],
            app.config["EMAIL_PASSWORD"],
        ),
    )
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(mail_formatter)
    logger.addHandler(mail_handler)
    app.logger.addHandler(mail_handler)
