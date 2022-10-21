import base64
import datetime
import os
import random
from io import BytesIO
from typing import Literal, NoReturn, Union

from flask import current_app, url_for
from flask_babel import gettext
from mongoengine import DateTimeField, Document, IntField, StringField
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app import APP_PATH, FILE_PATH
from app.exceptions import (
    VCodeCoolingError,
    VCodeExpiredError,
    VCodeNotExistError,
    VCodeWrongError,
)
from app.tasks.email import send_email
from app.constants.v_code import (
    VCodeType,
    VCodeTypes,
    VCodeContentType,
    VCodeContentTypes,
    VCodeAddressTypes,
)
from app.utils.logging import logger
from uuid import uuid4


class VCode(Document):
    meta = {"allow_inheritance": True}

    content: str = StringField(required=True, db_field="c")  # 验证码内容
    type: VCodeTypes = IntField(required=True, db_field="t")  # 验证码类型
    info: str = StringField(required=True, db_field="i")  # 验证码识别信息
    expires: datetime.datetime = DateTimeField(required=True, db_field="e")
    wrong_count: int = IntField(default=0, db_field="w")
    send_time: datetime.datetime = DateTimeField(db_field="s")  # 发送时间

    @classmethod
    def create(
        cls,
        code_type: VCodeTypes,
        code_info: str,
        content_type: VCodeContentTypes = VCodeContentType.NUMBER,
        content_len: int = 6,
        expires: int = 172800,
        wait: int = 0,
    ) -> "VCode":
        """
        生成验证码

        :param int content_type: 验证码随机数类型(数字,字符,数字+字符) 详见VCodeContentType
        :param int content_len: 验证码随机数长度
        :param int code_type: 验证码类型
        :param str code_info: 验证码识别信息
        :param int expires: 过期时间,默认2天(172800s)
        :param int wait: 等待时间,默认0s
        :param str case: 是否强制大小写('lower','upper')
        :rtype: VCode
        :return: 验证码对象
        """
        # 生成随机字符串
        if content_type == VCodeContentType.NUMBER:
            content_list = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
        elif content_type == VCodeContentType.LETTER:
            content_list = (
                "a",
                "b",
                "c",
                "d",
                "e",
                "f",
                "g",
                "h",
                "i",
                "j",
                "k",
                "l",
                "m",
                "n",
                "o",
                "p",
                "q",
                "r",
                "s",
                "t",
                "u",
                "v",
                "w",
                "x",
                "y",
                "z",
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "I",
                "J",
                "K",
                "L",
                "M",
                "N",
                "O",
                "P",
                "Q",
                "R",
                "S",
                "T",
                "U",
                "V",
                "W",
                "X",
                "Y",
                "Z",
            )
        else:
            content_list = (
                "0",
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "a",
                "b",
                "c",
                "d",
                "e",
                "f",
                "g",
                "h",
                "i",
                "j",
                "k",
                "l",
                "m",
                "n",
                "o",
                "p",
                "q",
                "r",
                "s",
                "t",
                "u",
                "v",
                "w",
                "x",
                "y",
                "z",
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "I",
                "J",
                "K",
                "L",
                "M",
                "N",
                "O",
                "P",
                "Q",
                "R",
                "S",
                "T",
                "U",
                "V",
                "W",
                "X",
                "Y",
                "Z",
            )
        random_str = "".join(random.sample(content_list, content_len))
        code = cls.objects(type=code_type, info=code_info).first()
        utcnow = datetime.datetime.utcnow()
        # 如果已经有同类型且验证信息一致的验证码
        if code:
            # 检测是否已等待足够时间
            if code.send_time:
                delta = (utcnow - code.send_time).seconds
                if delta < wait:
                    raise VCodeCoolingError(wait - delta)
            # 给予新的随机数,并更新时间,将错误次数归零
            code.content = random_str
            code.expires = utcnow + datetime.timedelta(seconds=expires)
            code.wrong_count = 0
            code.send_time = None
        # 没有这个验证码,生成一个新的
        else:
            code = cls(
                content=random_str,
                type=code_type,
                info=code_info,
                expires=(utcnow + datetime.timedelta(seconds=expires)),
            )
        code.save()
        return code

    @classmethod
    def verify(
        cls,
        code_type: VCodeTypes,
        code_info: str,
        code_content: str,
        case_sensitive=True,
        delete_after_verified=True,
    ) -> Union[Literal[True], NoReturn]:
        """
        检测验证码是否正确

        :param code_type: 验证码类型
        :param code_info: 验证码识别信息
        :param code_content: 验证码随机数
        :param case_sensitive: 是否对大小写敏感
        :param delete_after_verified: 通过验证后是否删除
        :return:
        """
        # 检查是否有此验证码
        code = cls.objects(type=code_type, info=code_info).first()
        # 如果存在
        if code:
            saved_code_content = code.content
            # 如果不区分大小写,则都转换为小写
            if not case_sensitive:
                saved_code_content = saved_code_content.lower()
                code_content = code_content.lower()
            # 检查验证码是否过期
            if code.expires > datetime.datetime.utcnow():
                # 如果验证码内容一致
                if saved_code_content == code_content:
                    # 通过验证后是否删除
                    if delete_after_verified:
                        code.delete()
                    return True
                # 验证码错误
                else:
                    # 如果现在为第五次尝试,则删除此验证码
                    if code.wrong_count >= 4:
                        code.delete()
                    else:
                        code.wrong_count += 1
                        code.save()
                    raise VCodeWrongError
            # 验证码过期
            else:
                code.delete()  # 过期则删除
                raise VCodeExpiredError
        # 验证码不存在
        else:
            raise VCodeNotExistError

    def to_log(self, address_type: VCodeAddressTypes, address: str) -> None:
        """
        发送邮箱地址确认验证码到邮箱

        :param address: 接收地址/手机号
        :return:
        """
        if self.type == VCodeType.RESET_EMAIL:
            logger.info(
                "Reset Email v_code {} - {} to ({}) {}".format(
                    self.content, self.info, address_type, address
                )
            )
        elif self.type == VCodeType.CONFIRM_EMAIL:
            logger.info(
                "Confirm Email v_code {} - {} to ({}) {}".format(
                    self.content, self.info, address_type, address
                )
            )
        elif self.type == VCodeType.RESET_PASSWORD:
            logger.info(
                "Reset Password v_code {} - {} to ({}) {}".format(
                    self.content, self.info, address_type, address
                )
            )
        else:
            raise RuntimeError("This v_code type not support to_log")

    def to_email(self, address: str) -> None:
        """
        发送验证码到邮箱

        :param address: 邮箱地址
        :param wait: 等待重发秒数
        :return:
        """
        email_subject_dict = {
            VCodeType.RESET_EMAIL: gettext("重置您的安全邮箱"),
            VCodeType.CONFIRM_EMAIL: gettext("确认您的安全邮箱"),
            VCodeType.RESET_PASSWORD: gettext("重置您的密码"),
        }
        email_template_dict = {
            VCodeType.RESET_EMAIL: "email/reset_email",
            VCodeType.CONFIRM_EMAIL: "email/confirm_email",
            VCodeType.RESET_PASSWORD: "email/reset_password",
        }
        if self.type not in email_subject_dict or self.type not in email_template_dict:
            raise RuntimeError("VCode({}) don't have email template".format(self.type))
        site_url = current_app.config.get("APP_SITE_URL")
        if (site_url is None):
            site_url = url_for('.index', _external=True)
        if current_app.config["DEBUG"] or current_app.config["TESTING"]:
            self.to_log("email", address)
        else:
            send_email(
                to_address=address,
                subject=email_subject_dict[self.type],
                template=email_template_dict[self.type],
                template_data={
                    'code': self.content,
                    'site_name': current_app.config.get("APP_SITE_NAME"),
                    'site_url': site_url
                },
            )
        self.send_time = datetime.datetime.utcnow()
        self.save()

    def to_sms(self, address: str) -> None:
        """
        发送验证码到短信

        :param address: 手机号
        :param wait: 等待重发秒数
        :return:
        """
        sms_template_code_dict = {
            VCodeType.RESET_PHONE: "1",
            VCodeType.CONFIRM_PHONE: "1",
            VCodeType.RESET_PASSWORD: "1",
        }
        if self.type not in sms_template_code_dict:
            raise RuntimeError("VCode({}) don't have sms template".format(self.type))
        if current_app.config["DEBUG"] or current_app.config["TESTING"]:
            self.to_log("sms", address)
        else:
            """发送短信验证码"""
        # 记录发送时间
        self.send_time = datetime.datetime.utcnow()
        self.save()


class Captcha(VCode):
    @classmethod
    def create(
        cls,
        content_type: VCodeContentTypes = VCodeContentType.NUMBER,
        content_len: int = 4,
        expires: int = 600,
        **kwargs
    ) -> "Captcha":
        """
        生成人机验证码（默认四位纯数字，过期时间10分钟）

        :param int content_type: 验证码随机数类型(数字,字符,数字+字符)
            详见VerificationCodeContentType
        :param int content_len: 验证码随机数长度
        :param expires: 过期时间 默认10分钟(600s)
        :rtype: Captcha
        :return: 验证码对象
        """
        return super().create(
            content_type=content_type,
            content_len=content_len,
            code_info=str(uuid4()),
            code_type=VCodeType.CAPTCHA,
            expires=expires,
            wait=0,
        )

    @classmethod
    def verify(
        cls, code_info: str, code_content: str, case_sensitive: bool = False, **kwargs
    ):
        """
        验证人机验证码（默认不区分大小写，验证正确后删除验证码）

        :param code_info:
        :param code_content:
        :param case_sensitive:
        :param kwargs:
        :return:
        """
        return super().verify(
            code_type=VCodeType.CAPTCHA,
            code_info=code_info,
            code_content=code_content,
            case_sensitive=case_sensitive,
        )

    def send(self, address: str) -> NoReturn:
        raise RuntimeError("Captcha can not send")

    def to_image(
        self,
        size=(120, 38),
        mode="RGB",
        bg_color=(255, 255, 255),
        font_size=23,
        font_path=os.path.abspath(os.path.join(FILE_PATH, "fonts", "captcha.ttf")),
        draw_lines=True,
        n_line=(1, 2),
        draw_points=True,
        point_chance=2,
    ):
        """
        生成验证码图片

        :param content: 生成的内容
        :param size: 图片的大小，格式（宽，高），默认为(120, 30)
        :param mode: 图片模式，默认为RGB
        :param bg_color: 背景颜色，默认为白色
        :param font_size: 验证码字体大小
        :param font_path: 验证码字体，默认为
        :param draw_lines: 是否划干扰线
        :param n_line: 干扰线的条数范围，格式元组，默认为(1, 2)，只有draw_lines为True时有效
        :param draw_points: 是否画干扰点
        :param point_chance: 干扰点出现的概率，大小范围[0, 100]
        @return: PIL Image实例
        """

        def _create_lines(draw, n_line, width, height):
            """绘制干扰线"""
            line_num = random.randint(n_line[0], n_line[1])  # 干扰线条数
            for i in range(line_num):
                # 起始点
                begin = (random.randint(0, width), random.randint(0, height))
                # 结束点
                end = (random.randint(0, width), random.randint(0, height))
                draw.line([begin, end], fill=(0, 0, 0))

        def _create_points(draw, point_chance, width, height):
            """绘制干扰点"""
            chance = min(100, max(0, int(point_chance)))  # 大小限制在[0, 100]
            for w in range(width):
                for h in range(height):
                    tmp = random.randint(0, 100)
                    if tmp > 100 - chance:
                        draw.point((w, h), fill=(0, 0, 0))

        width, height = size  # 宽， 高
        img = Image.new(mode, size, bg_color)  # 创建图形
        draw = ImageDraw.Draw(img)  # 创建画笔
        if draw_lines:
            _create_lines(draw, n_line, width, height)
        if draw_points:
            _create_points(draw, point_chance, width, height)
        font_path = os.path.join(APP_PATH, font_path)
        font = ImageFont.truetype(font_path, font_size)
        content_width, content_height = font.getsize(self.content)
        right_space = width / 10 * 2  # 右空白宽度
        left_space = 10  # 左空白宽度
        left_right_space = right_space + left_space
        space_width = (width - left_right_space - content_width) / (
            len(self.content) + 1
        )  # 所有字中间的空白
        if space_width < 0:
            space_width = 0
        left_padding = left_space + space_width  # 距离左边的距离
        for char in self.content:
            fg_colors = [(52, 152, 219)]
            fg_color = fg_colors[random.randint(0, len(fg_colors) - 1)]
            x, y = left_padding, (height - content_height) / 3
            draw.text((x, y), char, font=font, fill=fg_color)  # 画上画布
            left_padding += font.getsize(char)[0] + space_width
        # 图形扭曲参数
        params = [
            1 - float(random.randint(1, 2)) / 100,
            0,
            0,
            0,
            1 - float(random.randint(1, 10)) / 100,
            float(random.randint(1, 2)) / 500,
            0.001,
            float(random.randint(1, 2)) / 500,
        ]
        img = img.transform(size, Image.PERSPECTIVE, params)  # 创建扭曲
        img = img.filter(ImageFilter.EDGE_ENHANCE)  # 滤镜，边界加强（阈值更大）
        return img

    def to_base64(self) -> str:
        img = self.to_image()
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue())
        buffer.close()
        return "data:image/jpg;base64," + img_str.decode("utf8")
