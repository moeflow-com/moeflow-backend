import datetime

from flask_babel import gettext
from mongoengine import (
    Document,
    StringField,
    ReferenceField,
    DateTimeField,
    IntField,
    BooleanField,
)

from app.exceptions.message import MessageTypeError
from app.constants.message import MessageType


class Message(Document):
    sender = ReferenceField("User", db_field="s", required=True)  # 发送者
    receiver = ReferenceField("User", db_field="r", required=True)  # 接收人
    content = StringField(db_field="c", default="")  # 内容
    type = IntField(
        db_field="t", required=True
    )  # 站内信类型，根据不同类型，前端显示不同
    read = BooleanField(db_field="rd", default=False)  # 是否已读
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)

    @classmethod
    def send_system_message(cls, sender, receiver, content, message_type):
        """发送系统消息"""
        if message_type not in [
            MessageType.SYSTEM,
            MessageType.INVITE,
            MessageType.APPLY,
        ]:
            raise MessageTypeError(gettext("非系统消息类型"))
        message = cls(
            sender=sender,
            receiver=receiver,
            content=content,
            type=message_type,
        ).save()
        return message

    @classmethod
    def send_user_message(cls, sender, receiver, content):
        """发送用户消息"""
        message = cls(
            sender=sender,
            receiver=receiver,
            content=content,
            type=MessageType.USER,
        ).save()
        return message
