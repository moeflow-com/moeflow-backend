from flask_babel import gettext
from mongoengine import Document, BooleanField, StringField, IntField, QuerySet

from app.exceptions.language import LanguageNotExistError
from app.utils.logging import logger
from typing import List, Any, Dict


class Language(Document):
    en_name: str = StringField(db_field="e")  # 英文名称
    lo_name: str = StringField(db_field="c")  # 系统名称（中文），用于翻译成 i18n_name
    no_space: bool = BooleanField(db_field="n", default=False)  # 不用空格分割
    code: str = StringField(
        db_field="co", default="", unique=True
    )  # 语言code，用于代码中引用此语言，不可修改
    g_tra_code: str = StringField(db_field="gt", default="")  # 谷歌翻译 hint
    g_ocr_code: str = StringField(db_field="go", default="")  # 谷歌ocr hint
    sort: int = IntField(db_field="s", default=0)

    SYSTEM_LANGUAGES_DATA = [
        {
            "en_name": "Japanese",
            "lo_name": "日语",
            "code": "ja",
            "g_tra_code": "ja",
            "g_ocr_code": "ja",
            "no_space": True,
        },
        {
            "en_name": "English",
            "lo_name": "英语",
            "code": "en",
            "g_tra_code": "en",
            "g_ocr_code": "en",
        },
        {
            "en_name": "Korean",
            "lo_name": "朝鲜语（韩语）",
            "code": "ko",
            "g_tra_code": "ko",
            "g_ocr_code": "ko",
            "no_space": True,
        },
        {
            "en_name": "Chinese (Simplified)",
            "lo_name": "中文（简体）",
            "code": "zh-CN",
            "g_tra_code": "zh-CN",
            "g_ocr_code": "zh",
            "no_space": True,
        },
        {
            "en_name": "Chinese (Traditional)",
            "lo_name": "中文（繁体）",
            "code": "zh-TW",
            "g_tra_code": "zh-TW",
            "g_ocr_code": "zh",
            "no_space": True,
        },
        {
            "en_name": "Afrikaans",
            "lo_name": "南非荷兰语",
            "code": "af",
            "g_tra_code": "af",
            "g_ocr_code": "af",
        },
        {
            "en_name": "Albanian",
            "lo_name": "阿尔巴尼亚语",
            "code": "sq",
            "g_tra_code": "sq",
            "g_ocr_code": "",
        },
        {
            "en_name": "Amharic",
            "lo_name": "阿姆哈拉语",
            "code": "am",
            "g_tra_code": "am",
            "g_ocr_code": "",
        },
        {
            "en_name": "Assamese",
            "lo_name": "阿萨姆语",
            "code": "as",
            "g_tra_code": "",
            "g_ocr_code": "as",
        },
        {
            "en_name": "Arabic",
            "lo_name": "阿拉伯语",
            "code": "ar",
            "g_tra_code": "ar",
            "g_ocr_code": "ar",
        },
        {
            "en_name": "Armenian",
            "lo_name": "亚美尼亚语",
            "code": "hy",
            "g_tra_code": "hy",
            "g_ocr_code": "",
        },
        {
            "en_name": "Azerbaijani",
            "lo_name": "阿塞拜疆语",
            "code": "az",
            "g_tra_code": "az",
            "g_ocr_code": "az",
        },
        {
            "en_name": "Basque",
            "lo_name": "巴斯克语",
            "code": "eu",
            "g_tra_code": "eu",
            "g_ocr_code": "",
        },
        {
            "en_name": "Belarusian",
            "lo_name": "白俄罗斯语",
            "code": "be",
            "g_tra_code": "be",
            "g_ocr_code": "be",
        },
        {
            "en_name": "Bengali",
            "lo_name": "孟加拉语",
            "code": "bn",
            "g_tra_code": "bn",
            "g_ocr_code": "bn",
        },
        {
            "en_name": "Bosnian",
            "lo_name": "波斯尼亚语",
            "code": "bs",
            "g_tra_code": "bs",
            "g_ocr_code": "",
        },
        {
            "en_name": "Bulgarian",
            "lo_name": "保加利亚语",
            "code": "bg",
            "g_tra_code": "bg",
            "g_ocr_code": "bg",
        },
        {
            "en_name": "Catalan",
            "lo_name": "加泰罗尼亚语",
            "code": "ca",
            "g_tra_code": "ca",
            "g_ocr_code": "ca",
        },
        {
            "en_name": "Cebuano",
            "lo_name": "宿务语",
            "code": "ceb",
            "g_tra_code": "ceb",
            "g_ocr_code": "",
        },
        {
            "en_name": "Corsican",
            "lo_name": "科西嘉语",
            "code": "co",
            "g_tra_code": "co",
            "g_ocr_code": "",
        },
        {
            "en_name": "Croatian",
            "lo_name": "克罗地亚语",
            "code": "hr",
            "g_tra_code": "hr",
            "g_ocr_code": "hr",
        },
        {
            "en_name": "Czech",
            "lo_name": "捷克语",
            "code": "cs",
            "g_tra_code": "cs",
            "g_ocr_code": "cs",
        },
        {
            "en_name": "Danish",
            "lo_name": "丹麦语",
            "code": "da",
            "g_tra_code": "da",
            "g_ocr_code": "da",
        },
        {
            "en_name": "Dutch",
            "lo_name": "荷兰语",
            "code": "nl",
            "g_tra_code": "nl",
            "g_ocr_code": "nl",
        },
        {
            "en_name": "Esperanto",
            "lo_name": "世界语",
            "code": "eo",
            "g_tra_code": "eo",
            "g_ocr_code": "",
        },
        {
            "en_name": "Estonian",
            "lo_name": "爱沙尼亚语",
            "code": "et",
            "g_tra_code": "et",
            "g_ocr_code": "et",
        },
        {
            "en_name": "Finnish",
            "lo_name": "芬兰语",
            "code": "fi",
            "g_tra_code": "fi",
            "g_ocr_code": "fi",
        },
        {
            "en_name": "French",
            "lo_name": "法语",
            "code": "fr",
            "g_tra_code": "fr",
            "g_ocr_code": "fr",
        },
        {
            "en_name": "Frisian",
            "lo_name": "弗里斯兰语",
            "code": "fy",
            "g_tra_code": "fy",
            "g_ocr_code": "",
        },
        {
            "en_name": "Galician",
            "lo_name": "加利西亚语",
            "code": "gl",
            "g_tra_code": "gl",
            "g_ocr_code": "",
        },
        {
            "en_name": "Georgian",
            "lo_name": "格鲁吉亚语",
            "code": "ka",
            "g_tra_code": "ka",
            "g_ocr_code": "",
        },
        {
            "en_name": "German",
            "lo_name": "德语",
            "code": "de",
            "g_tra_code": "de",
            "g_ocr_code": "de",
        },
        {
            "en_name": "Greek",
            "lo_name": "希腊语",
            "code": "el",
            "g_tra_code": "el",
            "g_ocr_code": "el",
            "no_space": True,
        },
        {
            "en_name": "Gujarati",
            "lo_name": "古吉拉特语",
            "code": "gu",
            "g_tra_code": "gu",
            "g_ocr_code": "",
        },
        {
            "en_name": "Haitian Creole",
            "lo_name": "海地克里奥尔语",
            "code": "ht",
            "g_tra_code": "ht",
            "g_ocr_code": "",
        },
        {
            "en_name": "Hausa",
            "lo_name": "豪萨语",
            "code": "ha",
            "g_tra_code": "ha",
            "g_ocr_code": "",
        },
        {
            "en_name": "Hawaiian",
            "lo_name": "夏威夷语",
            "code": "haw",
            "g_tra_code": "haw",
            "g_ocr_code": "",
        },
        {
            "en_name": "Hebrew",
            "lo_name": "希伯来语",
            "code": "iw",
            "g_tra_code": "iw",
            "g_ocr_code": "iw",
        },
        {
            "en_name": "Hindi",
            "lo_name": "印地语",
            "code": "hi",
            "g_tra_code": "hi",
            "g_ocr_code": "hi",
        },
        {
            "en_name": "Hmong",
            "lo_name": "苗语",
            "code": "hmn",
            "g_tra_code": "hmn",
            "g_ocr_code": "",
        },
        {
            "en_name": "Hungarian",
            "lo_name": "匈牙利语",
            "code": "hu",
            "g_tra_code": "hu",
            "g_ocr_code": "hu",
        },
        {
            "en_name": "Icelandic",
            "lo_name": "冰岛语",
            "code": "is",
            "g_tra_code": "is",
            "g_ocr_code": "is",
        },
        {
            "en_name": "Igbo",
            "lo_name": "伊博语",
            "code": "ig",
            "g_tra_code": "ig",
            "g_ocr_code": "",
        },
        {
            "en_name": "Indonesian",
            "lo_name": "印度尼西亚语",
            "code": "id",
            "g_tra_code": "id",
            "g_ocr_code": "id",
        },
        {
            "en_name": "Irish",
            "lo_name": "爱尔兰语",
            "code": "ga",
            "g_tra_code": "ga",
            "g_ocr_code": "",
        },
        {
            "en_name": "Italian",
            "lo_name": "意大利语",
            "code": "it",
            "g_tra_code": "it",
            "g_ocr_code": "it",
        },
        {
            "en_name": "Javanese",
            "lo_name": "爪哇语",
            "code": "jw",
            "g_tra_code": "jw",
            "g_ocr_code": "",
            "no_space": True,
        },
        {
            "en_name": "Kannada",
            "lo_name": "卡纳达语",
            "code": "kn",
            "g_tra_code": "kn",
            "g_ocr_code": "",
        },
        {
            "en_name": "Kazakh",
            "lo_name": "哈萨克语",
            "code": "kk",
            "g_tra_code": "kk",
            "g_ocr_code": "kk",
        },
        {
            "en_name": "Khmer",
            "lo_name": "高棉语",
            "code": "km",
            "g_tra_code": "km",
            "g_ocr_code": "",
            "no_space": True,
        },
        {
            "en_name": "Kurdish",
            "lo_name": "库尔德语",
            "code": "ku",
            "g_tra_code": "ku",
            "g_ocr_code": "",
        },
        {
            "en_name": "Kyrgyz",
            "lo_name": "吉尔吉斯语",
            "code": "ky",
            "g_tra_code": "ky",
            "g_ocr_code": "ky",
        },
        {
            "en_name": "Lao",
            "lo_name": "老挝语",
            "code": "lo",
            "g_tra_code": "lo",
            "g_ocr_code": "",
            "no_space": True,
        },
        {
            "en_name": "Latin",
            "lo_name": "拉丁语",
            "code": "la",
            "g_tra_code": "la",
            "g_ocr_code": "",
            "no_space": True,
        },
        {
            "en_name": "Latvian",
            "lo_name": "拉脱维亚语",
            "code": "lv",
            "g_tra_code": "lv",
            "g_ocr_code": "lv",
        },
        {
            "en_name": "Lithuanian",
            "lo_name": "立陶宛语",
            "code": "lt",
            "g_tra_code": "lt",
            "g_ocr_code": "lt",
        },
        {
            "en_name": "Luxembourgish",
            "lo_name": "卢森堡语",
            "code": "lb",
            "g_tra_code": "lb",
            "g_ocr_code": "",
        },
        {
            "en_name": "Macedonian",
            "lo_name": "马其顿语",
            "code": "mk",
            "g_tra_code": "mk",
            "g_ocr_code": "mk",
        },
        {
            "en_name": "Malagasy",
            "lo_name": "马尔加什语",
            "code": "mg",
            "g_tra_code": "mg",
            "g_ocr_code": "",
        },
        {
            "en_name": "Malay",
            "lo_name": "马来语",
            "code": "ms",
            "g_tra_code": "ms",
            "g_ocr_code": "",
        },
        {
            "en_name": "Malayalam",
            "lo_name": "马拉雅拉姆语",
            "code": "ml",
            "g_tra_code": "ml",
            "g_ocr_code": "",
        },
        {
            "en_name": "Maltese",
            "lo_name": "马耳他语",
            "code": "mt",
            "g_tra_code": "mt",
            "g_ocr_code": "",
        },
        {
            "en_name": "Maori",
            "lo_name": "毛利语",
            "code": "mi",
            "g_tra_code": "mi",
            "g_ocr_code": "",
        },
        {
            "en_name": "Marathi",
            "lo_name": "马拉语",
            "code": "mr",
            "g_tra_code": "mr",
            "g_ocr_code": "mr",
        },
        {
            "en_name": "Mongolian",
            "lo_name": "蒙古语",
            "code": "mn",
            "g_tra_code": "mn",
            "g_ocr_code": "mn",
        },
        {
            "en_name": "Myanmar (Burmese)",
            "lo_name": "缅甸语",
            "code": "my",
            "g_tra_code": "my",
            "g_ocr_code": "",
            "no_space": True,
        },
        {
            "en_name": "Nepali",
            "lo_name": "尼泊尔语",
            "code": "ne",
            "g_tra_code": "ne",
            "g_ocr_code": "ne",
        },
        {
            "en_name": "Norwegian",
            "lo_name": "挪威语",
            "code": "no",
            "g_tra_code": "no",
            "g_ocr_code": "no",
        },
        {
            "en_name": "Nyanja (Chichewa)",
            "lo_name": "齐切瓦语",
            "code": "ny",
            "g_tra_code": "ny",
            "g_ocr_code": "",
        },
        {
            "en_name": "Pashto",
            "lo_name": "普什图语",
            "code": "ps",
            "g_tra_code": "ps",
            "g_ocr_code": "ps",
        },
        {
            "en_name": "Persian",
            "lo_name": "波斯语",
            "code": "fa",
            "g_tra_code": "fa",
            "g_ocr_code": "fa",
        },
        {
            "en_name": "Polish",
            "lo_name": "波兰语",
            "code": "pl",
            "g_tra_code": "pl",
            "g_ocr_code": "pl",
        },
        {
            "en_name": "Portuguese (Portugal, Brazil)",
            "lo_name": "葡萄牙语",
            "code": "pt",
            "g_tra_code": "pt",
            "g_ocr_code": "pt",
        },
        {
            "en_name": "Punjabi",
            "lo_name": "旁遮普语",
            "code": "pa",
            "g_tra_code": "pa",
            "g_ocr_code": "",
        },
        {
            "en_name": "Romanian",
            "lo_name": "罗马尼亚语",
            "code": "ro",
            "g_tra_code": "ro",
            "g_ocr_code": "ro",
        },
        {
            "en_name": "Russian",
            "lo_name": "俄语",
            "code": "ru",
            "g_tra_code": "ru",
            "g_ocr_code": "ru",
        },
        {
            "en_name": "Samoan",
            "lo_name": "萨摩亚语",
            "code": "sm",
            "g_tra_code": "sm",
            "g_ocr_code": "",
        },
        {
            "en_name": "Scots Gaelic",
            "lo_name": "苏格兰盖尔语",
            "code": "gd",
            "g_tra_code": "gd",
            "g_ocr_code": "",
        },
        {
            "en_name": "Sanskrit",
            "lo_name": "梵文",
            "code": "sa",
            "g_tra_code": "",
            "g_ocr_code": "sa",
        },
        {
            "en_name": "Serbian",
            "lo_name": "塞尔维亚语",
            "code": "sr",
            "g_tra_code": "sr",
            "g_ocr_code": "sr",
        },
        {
            "en_name": "Sesotho",
            "lo_name": "塞索托语",
            "code": "st",
            "g_tra_code": "st",
            "g_ocr_code": "",
        },
        {
            "en_name": "Shona",
            "lo_name": "绍纳语",
            "code": "sn",
            "g_tra_code": "sn",
            "g_ocr_code": "",
        },
        {
            "en_name": "Sindhi",
            "lo_name": "信德语",
            "code": "sd",
            "g_tra_code": "sd",
            "g_ocr_code": "",
        },
        {
            "en_name": "Sinhala (Sinhalese)",
            "lo_name": "僧伽罗语",
            "code": "si",
            "g_tra_code": "si",
            "g_ocr_code": "",
        },
        {
            "en_name": "Slovak",
            "lo_name": "斯洛伐克语",
            "code": "sk",
            "g_tra_code": "sk",
            "g_ocr_code": "sk",
        },
        {
            "en_name": "Slovenian",
            "lo_name": "斯卡洛文语",
            "code": "sl",
            "g_tra_code": "sl",
            "g_ocr_code": "sl",
        },
        {
            "en_name": "Somali",
            "lo_name": "索马里语",
            "code": "so",
            "g_tra_code": "so",
            "g_ocr_code": "",
        },
        {
            "en_name": "Spanish",
            "lo_name": "西班牙语",
            "code": "es",
            "g_tra_code": "es",
            "g_ocr_code": "es",
        },
        {
            "en_name": "Sundanese",
            "lo_name": "巽他语",
            "code": "su",
            "g_tra_code": "su",
            "g_ocr_code": "",
        },
        {
            "en_name": "Swahili",
            "lo_name": "斯瓦希里语",
            "code": "sw",
            "g_tra_code": "sw",
            "g_ocr_code": "",
        },
        {
            "en_name": "Swedish",
            "lo_name": "瑞典语",
            "code": "sv",
            "g_tra_code": "sv",
            "g_ocr_code": "sv",
        },
        {
            "en_name": "Tagalog (Filipino)",
            "lo_name": "他加禄语（菲律宾语）",
            "code": "tl",
            "g_tra_code": "tl",
            "g_ocr_code": "tl",
        },
        {
            "en_name": "Tajik",
            "lo_name": "塔吉克语",
            "code": "tg",
            "g_tra_code": "tg",
            "g_ocr_code": "",
        },
        {
            "en_name": "Tamil",
            "lo_name": "泰米尔语",
            "code": "ta",
            "g_tra_code": "ta",
            "g_ocr_code": "ta",
        },
        {
            "en_name": "Telugu",
            "lo_name": "泰卢固语",
            "code": "te",
            "g_tra_code": "te",
            "g_ocr_code": "",
        },
        {
            "en_name": "Thai",
            "lo_name": "泰语",
            "code": "th",
            "g_tra_code": "th",
            "g_ocr_code": "th",
        },
        {
            "en_name": "Turkish",
            "lo_name": "土耳其语",
            "code": "tr",
            "g_tra_code": "tr",
            "g_ocr_code": "tr",
        },
        {
            "en_name": "Ukrainian",
            "lo_name": "乌克兰语",
            "code": "uk",
            "g_tra_code": "uk",
            "g_ocr_code": "uk",
        },
        {
            "en_name": "Urdu",
            "lo_name": "乌尔都语",
            "code": "ur",
            "g_tra_code": "ur",
            "g_ocr_code": "ur",
        },
        {
            "en_name": "Uzbek",
            "lo_name": "乌兹别克语",
            "code": "uz",
            "g_tra_code": "uz",
            "g_ocr_code": "uz",
        },
        {
            "en_name": "Vietnamese",
            "lo_name": "越南语",
            "code": "vi",
            "g_tra_code": "vi",
            "g_ocr_code": "vi",
        },
        {
            "en_name": "Welsh",
            "lo_name": "威尔士语",
            "code": "cy",
            "g_tra_code": "cy",
            "g_ocr_code": "",
        },
        {
            "en_name": "Xhosa",
            "lo_name": "科萨语",
            "code": "xh",
            "g_tra_code": "xh",
            "g_ocr_code": "",
        },
        {
            "en_name": "Yiddish",
            "lo_name": "意第绪语",
            "code": "yi",
            "g_tra_code": "yi",
            "g_ocr_code": "",
        },
        {
            "en_name": "Yoruba",
            "lo_name": "约鲁巴语",
            "code": "yo",
            "g_tra_code": "yo",
            "g_ocr_code": "",
        },
        {
            "en_name": "Zulu",
            "lo_name": "祖鲁语",
            "code": "zu",
            "g_tra_code": "zu",
            "g_ocr_code": "",
        },
    ]

    @classmethod
    def init_system_languages(cls) -> None:
        """初始化语言表"""
        logger.info("-" * 50)
        if cls.objects.count() > 0:
            logger.info("已存在语言表，跳过初始化")
            return
        sort = 0
        for l in cls.SYSTEM_LANGUAGES_DATA:
            cls(
                en_name=l["en_name"],
                lo_name=l["lo_name"],
                no_space=l.get("no_space", False),
                code=l["code"],
                g_tra_code=l["g_tra_code"],
                g_ocr_code=l["g_ocr_code"],
                sort=sort,
            ).save()
            sort += 1
        logger.info(f"初始化语言表，共添加{len(cls.SYSTEM_LANGUAGES_DATA)}种语言")

    @classmethod
    def create(
        cls,
        code: str,
        en_name: str,
        lo_name: str,
        no_space=False,
        g_tra_code="",
        g_ocr_code="",
        sort=0,
    ) -> "Language":
        language = cls(
            en_name=en_name,
            lo_name=lo_name,
            no_space=no_space,
            code=code,
            g_tra_code=g_tra_code,
            g_ocr_code=g_ocr_code,
            sort=sort,
        )
        language.save()
        return language

    @property
    def i18n_name(self) -> str:
        """返回i18n名称"""
        return gettext(self.lo_name)

    @property
    def g_tra(self) -> bool:
        """是否支持谷歌翻译"""
        if self.g_tra_code:
            return True
        return False

    @property
    def g_ocr(self) -> bool:
        """是否支持谷歌OCR"""
        if self.g_ocr_code:
            return True
        return False

    @classmethod
    def by_id(cls, id: str) -> "Language":
        language = cls.objects(id=id).first()
        if language is None:
            raise LanguageNotExistError
        return language

    @classmethod
    def by_ids(cls, ids: List[str]) -> List["Language"]:
        # ids 去重
        ids = list(set(ids))
        languages = cls.objects(id__in=ids)
        languages_count = languages.count()
        # 未找到语言 或 缺少语言
        if languages_count == 0 or languages_count != len(ids):
            raise LanguageNotExistError
        return languages

    @classmethod
    def by_code(cls, code: str) -> "Language":
        language = cls.objects(code=code).first()
        if language is None:
            raise LanguageNotExistError
        return language

    @classmethod
    def by_codes(cls, codes: List[str]) -> List["Language"]:
        # codes 去重
        codes = list(set(codes))
        languages = cls.objects(code__in=codes)
        languages_count = languages.count()
        # 未找到语言 或 缺少语言
        if languages_count == 0 or languages_count != len(codes):
            raise LanguageNotExistError
        return languages

    @classmethod
    def get(cls) -> QuerySet:
        """返回所有语言"""
        return cls.objects(code__ne="").order_by("sort")

    @classmethod
    def ids(cls) -> List[str]:
        return [str(id) for id in cls.get().scalar("id")]

    @classmethod
    def codes(cls) -> List[str]:
        return [str(code) for code in cls.get().scalar("code")]

    def clear(self) -> None:
        """禁止删除语言"""
        pass

    def to_api(self) -> Dict[str, Any]:
        """
        @apiDefine LanguageInfoModel
        @apiSuccess {String} id ID
        """
        return {
            "id": str(self.id),
            "en_name": self.en_name,
            "lo_name": self.lo_name,
            "i18n_name": self.i18n_name,
            "no_space": self.no_space,
            "code": self.code,
            "g_tra_code": self.g_tra_code,
            "g_ocr_code": self.g_ocr_code,
            "sort": self.sort,
        }
