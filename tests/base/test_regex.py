import re

from app.regexs import EMAIL_REGEX
from tests import MoeTestCase


class RegexTestCase(MoeTestCase):
    def test_email_regex(self):
        # 禁止的邮箱格式
        self.assertIsNone(re.match(EMAIL_REGEX, "a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a."))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa."))
        self.assertIsNone(re.match(EMAIL_REGEX, "a.a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa.a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a.aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa.aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a."))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa."))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@.a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@.aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a..c"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa..c"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a..aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa..aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a..aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa..aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a...aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa...aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@.aaa.aaa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a.a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a.a.a.a.a.a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa.a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a.a."))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa.aaa."))
        self.assertIsNone(re.match(EMAIL_REGEX, "aaa@aaa.网"))
        # 多个 @
        self.assertIsNone(re.match(EMAIL_REGEX, "@aa@aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a@a@aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@@aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@a@a.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa@.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa.@aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa.a@a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa.aa@"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@@@aa.aa"))
        # 空格
        self.assertIsNone(re.match(EMAIL_REGEX, " aa@aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "a a@aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa @aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@ aa.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@a a.aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa .aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa. aa"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa.a a"))
        self.assertIsNone(re.match(EMAIL_REGEX, "aa@aa.aa "))
        # 允许个邮箱格式（只要符合 x@x.xx的都允许）
        self.assertIsNotNone(re.match(EMAIL_REGEX, "a@a.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "aa@aa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "aaa@aaa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "aaa.aaa@aaa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "aaa.aaa.aaa@aaa.aaa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "万维网.aaa.cn@万维网.aaa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "aaa.aaa+aaa+123@aaa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "aaa...aaa@aaa.aa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "...aaa...aaa...@aaa.aa"))
        # 后缀
        self.assertIsNotNone(re.match(EMAIL_REGEX, "a@a.aaa"))
        self.assertIsNotNone(re.match(EMAIL_REGEX, "a@a.aaaa"))
        # 其他
        self.assertIsNotNone(re.match(EMAIL_REGEX, "万维网.网站+子网@万维网.网站"))
        self.assertIsNotNone(
            re.match(EMAIL_REGEX, "aaaaaaaaaaaaa@aaaaaaaaaaaaa.aaaaaaaaaaaaa")
        )
