from app.models.language import Language
from app.models.team import Team
from tests import MoeTestCase


class LanguageModelTestCase(MoeTestCase):
    def test_no_space_languages(self):
        """中文肯定在无空格语言中"""
        self.assertTrue(Language.by_code("zh-CN").no_space)
        self.assertFalse(Language.by_code("en").no_space)

    def test_g_code(self):
        """测试谷歌翻译和OCR"""
        # 中文都支持
        self.assertTrue(Language.by_code("zh-CN").g_tra)
        self.assertTrue(Language.by_code("zh-CN").g_ocr)
        # 梵文只支持ocr
        self.assertFalse(Language.by_code("sa").g_tra)
        self.assertTrue(Language.by_code("sa").g_ocr)
        # 巽他语支持tra
        self.assertTrue(Language.by_code("su").g_tra)
        self.assertFalse(Language.by_code("su").g_ocr)

    def test_get_languages(self):
        """测试获取languages"""
        Team.create("t1")
        Team.create("t2")
        language_count = Language.objects.count()
        # 获取所有语言
        self.assertEqual(language_count, Language.get().count())
        # 新增了两个语言
        Language.create("code1", "test_language", "c", sort=10)  # 创建系统语言
        Language.create("code2", "test_language", "c")  # 创建项目语言
        self.assertEqual(language_count + 2, Language.objects.count())
        self.assertEqual(2, Language.objects(en_name="test_language").count())

    def test_delete_project(self):
        """测试删除项目会同时删除相应Language"""
        team1 = Team.create("t1")
        team2 = Team.create("t2")
        language_count = Language.objects.count()
        # 新增了两个语言
        Language.create("code1", "test_language", "c")  # 创建系统语言
        Language.create("code2", "test_language", "c")  # 创建项目语言
        self.assertEqual(language_count + 2, Language.objects.count())
        self.assertEqual(2, Language.objects(en_name="test_language").count())
        # 删除团队2，没有影响
        team2.clear()
        self.assertEqual(language_count + 2, Language.objects.count())
        self.assertEqual(2, Language.objects(en_name="test_language").count())
        # 删除团队1，没有影响
        team1.clear()
        self.assertEqual(language_count + 2, Language.objects.count())
        self.assertEqual(2, Language.objects(en_name="test_language").count())
