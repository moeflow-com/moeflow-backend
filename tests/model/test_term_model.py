import os

from app.exceptions.language import TargetAndSourceLanguageSameError
from app.models.language import Language
from app.models.project import Project
from app.models.team import Team
from app.models.term import Term, TermBank
from app.models.user import User
from tests import TEST_FILE_PATH, MoeTestCase


class TermModelTestCase(MoeTestCase):
    def setUp(self):
        super().setUp()
        self.JA = Language.by_code("ja")
        self.CN = Language.by_code("zh-CN")
        self.user = User(name="u1", email="u1").save()
        self.team = Team.create("t1", creator=self.user)
        self.project = Project.create("p1", self.team, creator=self.user)

    def test_add_delete_term(self):
        """测试增加、删除 术语、术语库"""
        # 术语库原语言和目标语言不能相同
        with self.assertRaises(TargetAndSourceLanguageSameError):
            TermBank.create(
                "term", self.team, self.JA, self.JA, user=self.user
            )
        # 增加术语库
        term_bank = TermBank.create(
            "term", self.team, self.JA, self.CN, user=self.user
        )
        self.assertEqual(TermBank.objects.count(), 1)
        self.assertEqual(term_bank.team, self.team)
        # 增加术语
        term = Term.create(term_bank, "原文", "译文", user=self.user, tip="小提示")
        self.assertEqual(Term.objects.count(), 1)
        self.assertEqual(term.term_bank, term_bank)
        self.assertEqual(term.term_bank.team, self.team)
        term2 = Term.create(
            term_bank, "原文2", "译文2", user=self.user, tip="小提示2"
        )
        self.assertEqual(Term.objects.count(), 2)
        self.assertEqual(term.term_bank, term_bank)
        self.assertEqual(term.term_bank.team, self.team)
        # 删除术语
        term2.clear()
        self.assertEqual(Term.objects.count(), 1)
        # 删除术语库
        term_bank.clear()
        self.assertEqual(TermBank.objects.count(), 0)
        self.assertEqual(Term.objects.count(), 0)

    def test_set_project_term_bank(self):
        """测试设置项目使用的术语库"""
        term_bank = TermBank.create(
            "term", self.team, self.JA, self.CN, user=self.user
        )
        self.project.term_banks = [term_bank]
        self.project.save()
        self.assertTrue(self.project.need_find_terms)  # 需要更新术语
        self.project.find_terms()
        self.project.reload()
        self.assertEqual(self.project.term_banks, [term_bank])
        # 删除术语库
        term_bank.clear()
        # 这时候应该是空数组了
        self.project.reload()
        self.assertEqual(self.project.term_banks, [])

    def test_find_term_where_set_term(self):
        """测试设置项目所用term时，自动匹配术语"""
        # 创建术语库
        term_bank = TermBank.create(
            "term", self.team, self.JA, self.CN, user=self.user
        )
        # 创建术语
        term1 = Term.create(term_bank, "Hello", "term1", user=self.user)
        term2 = Term.create(term_bank, "你好", "term2", user=self.user)
        # 上传文件
        with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as f:
            file = self.project.upload("term.txt", f)
        # 上传完指定术语库
        self.project.term_banks = [term_bank]
        self.project.save()
        self.assertTrue(self.project.need_find_terms)  # 需要更新术语
        self.project.find_terms()
        # source0没有可能的术语
        self.assertEqual(len(file.sources()[0].possible_terms), 0)
        # term1在source1中
        self.assertIn(term1, file.sources()[1].possible_terms)
        self.assertNotIn(term2, file.sources()[1].possible_terms)
        # term1，term2在source2中
        self.assertIn(term1, file.sources()[2].possible_terms)
        self.assertIn(term2, file.sources()[2].possible_terms)

    def test_find_term_where_upload(self):
        """测试当项目已经指定术语库时匹配术语"""
        # 创建术语库
        term_bank = TermBank.create(
            "term", self.team, self.JA, self.CN, user=self.user
        )
        # 创建术语
        term1 = Term.create(term_bank, "Hello", "term1", user=self.user)
        term2 = Term.create(term_bank, "你好", "term2", user=self.user)
        # 先指定术语库
        self.project.term_banks = [term_bank]
        self.project.save()
        self.assertTrue(self.project.need_find_terms)  # 需要更新术语
        self.project.find_terms()
        # 上传文件
        with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as f:
            file = self.project.upload("term.txt", f)
        # source0没有可能的术语
        self.assertEqual(len(file.sources()[0].possible_terms), 0)
        # term1在source1中
        self.assertIn(term1, file.sources()[1].possible_terms)
        self.assertNotIn(term2, file.sources()[1].possible_terms)
        # term1，term2在source2中
        self.assertIn(term1, file.sources()[2].possible_terms)
        self.assertIn(term2, file.sources()[2].possible_terms)

    def test_find_term_where_upload_and_set_term(self):
        """
        先设置一个术语，然后上传文件，然后再设置一个术语
        :return:
        """
        # 创建术语库
        term_bank = TermBank.create(
            "term", self.team, self.JA, self.CN, user=self.user
        )
        # 创建术语
        term1 = Term.create(term_bank, "Hello", "term1", user=self.user)
        # 先指定术语库
        self.project.term_banks = [term_bank]
        self.project.save()
        self.assertTrue(self.project.need_find_terms)  # 需要更新术语
        self.project.find_terms()
        # 上传文件
        with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as f:
            file = self.project.upload("term.txt", f)
        # 再设置一个术语
        term2 = Term.create(term_bank, "你好", "term2", user=self.user)
        # 刷新项目的术语
        self.project.find_terms()
        # source0没有可能的术语
        self.assertEqual(len(file.sources()[0].possible_terms), 0)
        # term1在source1中
        self.assertIn(term1, file.sources()[1].possible_terms)
        self.assertNotIn(term2, file.sources()[1].possible_terms)
        # term1，term2在source2中
        self.assertIn(term1, file.sources()[2].possible_terms)
        self.assertIn(term2, file.sources()[2].possible_terms)

    def test_pull_term(self):
        """测试当删除术语库或者术语时，关联的source的可能的术语会字段被pull"""
        # 创建术语库
        term_bank = TermBank.create(
            "term", self.team, self.JA, self.CN, user=self.user
        )
        # 创建术语
        term1 = Term.create(term_bank, "Hello", "term1", user=self.user)
        term2 = Term.create(term_bank, "你好", "term2", user=self.user)
        # 先指定术语库
        self.project.term_banks = [term_bank]
        self.project.save()
        self.assertTrue(self.project.need_find_terms)  # 需要更新术语
        self.project.find_terms()
        # 上传文件
        with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as f:
            file = self.project.upload("term.txt", f)
        # source0没有可能的术语
        self.assertEqual(len(file.sources()[0].possible_terms), 0)
        # term1在source1中
        self.assertIn(term1, file.sources()[1].possible_terms)
        self.assertNotIn(term2, file.sources()[1].possible_terms)
        # term1，term2在source2中
        self.assertIn(term1, file.sources()[2].possible_terms)
        self.assertIn(term2, file.sources()[2].possible_terms)

        # 删除术语term1
        term1.clear()
        # source0没有可能的术语
        self.assertEqual(len(file.sources()[0].possible_terms), 0)
        # term1不在source1中了
        self.assertEqual(len(file.sources()[1].possible_terms), 0)
        # term1不在source2中了，term2在source2中
        self.assertNotIn(term1, file.sources()[2].possible_terms)
        self.assertIn(term2, file.sources()[2].possible_terms)

        # 删除术语库
        term_bank.clear()
        # source0没有可能的术语
        self.assertEqual(len(file.sources()[0].possible_terms), 0)
        # source1没有可能的术语
        self.assertEqual(len(file.sources()[1].possible_terms), 0)
        # source2没有可能的术语
        self.assertEqual(len(file.sources()[2].possible_terms), 0)

    def test_need_find_terms(self):
        """
        测试更新创建术语库时，提示需要刷新相关项目
        """
        team = Team.create("t")
        project1 = Project.create("p1", team=team)
        project2 = Project.create("p2", team=team)
        project3 = Project.create("p3", team=team)
        # 创建完都无需更新
        self.assertFalse(project1.need_find_terms)
        self.assertFalse(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)
        # 创建术语库
        term_bank = TermBank.create(
            "tb", team, self.JA, self.CN, user=self.user
        ).save()
        term = Term.create(
            term_bank=term_bank, source="s", target="t", user=self.user
        ).save()
        # 给project1添加术语库，project1需要更新
        project1.term_banks = [term_bank]
        project2.term_banks = [term_bank]
        project1.save()
        project2.save()
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertTrue(project1.need_find_terms)
        self.assertTrue(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)
        # 寻找后更新关闭
        project1.find_terms()
        project2.find_terms()
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertFalse(project1.need_find_terms)
        self.assertFalse(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)

        # 修改term的target，不提示更新
        term.edit("s", "tt")
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertFalse(project1.need_find_terms)
        self.assertFalse(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)

        # 修改term的source，提示更新
        term.edit("ss", "t")
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertTrue(project1.need_find_terms)
        self.assertTrue(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)
        # 寻找后更新关闭
        project1.find_terms()
        project2.find_terms()
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertFalse(project1.need_find_terms)
        self.assertFalse(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)

        # 为term_bank新增term，提示更新
        Term.create(
            term_bank=term_bank, source="s2", target="t2", user=self.user
        ).save()
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertTrue(project1.need_find_terms)
        self.assertTrue(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)
        # 寻找后更新关闭
        project1.find_terms()
        project2.find_terms()
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertFalse(project1.need_find_terms)
        self.assertFalse(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)

        # 删除term2，不提示更新
        term.clear()
        # 检测
        project1.reload()
        project2.reload()
        project3.reload()
        self.assertFalse(project1.need_find_terms)
        self.assertFalse(project2.need_find_terms)
        self.assertFalse(project3.need_find_terms)
