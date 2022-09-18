from mongoengine import DoesNotExist

from app.exceptions import (
    NeedTokenError,
    NoPermissionError,
    TargetAndSourceLanguageSameError,
)
from app.models.language import Language
from app.models.team import Team
from app.models.term import Term, TermBank
from app.models.user import User
from tests import MoeAPITestCase


class TermAPITestCase(MoeAPITestCase):
    def test_get_term_bank(self):
        """测试获取术语库"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        team2 = Team.create("t2", creator=user2)
        user1.join(team2)
        # 建立术语库
        TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user1,
        )
        TermBank.create(
            name="tb2",
            team=team2,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user2,
        )
        # == 开始测试 ==
        # == 没有登录没有权限获取 ==
        data = self.get(f"/v1/teams/{str(team1.id)}/term-banks")
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没有权限获取 ==
        data = self.get(f"/v1/teams/{str(team1.id)}/term-banks", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # == 正常获取 ==
        data = self.get(f"/v1/teams/{str(team1.id)}/term-banks", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual("tb1", data.json[0]["name"])
        self.assertEqual("1", data.headers.get("X-Pagination-Count"))
        # == 正常获取team2的术语库 ==
        data = self.get(f"/v1/teams/{str(team2.id)}/term-banks", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual("tb2", data.json[0]["name"])
        self.assertEqual("1", data.headers.get("X-Pagination-Count"))
        # == 通过word搜索 ==
        # 再给team1创建一个术语库
        TermBank.create(
            name="tb3",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user1,
        )
        # word=B
        data = self.get(
            f"/v1/teams/{str(team1.id)}/term-banks",
            query_string={"word": "B"},
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual("2", data.headers.get("X-Pagination-Count"))
        # word=3
        data = self.get(
            f"/v1/teams/{str(team1.id)}/term-banks",
            query_string={"word": "3"},
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual("tb3", data.json[0]["name"])
        self.assertEqual("1", data.headers.get("X-Pagination-Count"))

    def test_create_term_bank(self):
        """测试创建术语库"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        team2 = Team.create("t2", creator=user2)
        user1.join(team2)
        # == 没登录无法创建 ==
        data = self.post(
            f"/v1/teams/{str(team1.id)}/term-banks",
            json={
                "name": "tb1",
                "tip": "it is tb1",
                "source_language_id": str(Language.by_code("zh-CN").id),
                "target_language_id": str(Language.by_code("zh-CN").id),
            },
        )
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没权限创建 ==
        data = self.post(
            f"/v1/teams/{str(team1.id)}/term-banks",
            json={
                "name": "tb1",
                "tip": "it is tb1",
                "source_language_id": str(Language.by_code("zh-CN").id),
                "target_language_id": str(Language.by_code("zh-CN").id),
            },
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # == 目标语言和原语言不能相同 ==
        data = self.post(
            f"/v1/teams/{str(team1.id)}/term-banks",
            json={
                "name": "tb1",
                "tip": "it is tb1",
                "source_language_id": str(Language.by_code("zh-CN").id),
                "target_language_id": str(Language.by_code("zh-CN").id),
            },
            token=token1,
        )
        self.assertErrorEqual(data, TargetAndSourceLanguageSameError)
        # == 正常创建 ==
        self.assertEqual(0, TermBank.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/term-banks",
            json={
                "name": "tb1",
                "tip": "it is tb1",
                "source_language_id": str(Language.by_code("zh-CN").id),
                "target_language_id": str(Language.by_code("ja").id),
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, team1.term_banks().count())
        self.assertEqual(0, team2.term_banks().count())
        self.assertEqual(1, TermBank.objects.count())
        tb1 = TermBank.objects(name="tb1").first()
        self.assertEqual(team1, tb1.team)
        self.assertEqual(user1, tb1.user)
        self.assertEqual(Language.by_code("zh-CN"), tb1.source_language)
        self.assertEqual(Language.by_code("ja"), tb1.target_language)
        self.assertEqual("tb1", tb1.name)
        self.assertEqual("it is tb1", tb1.tip)

    def test_edit_term_bank(self):
        """测试修改术语库"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        # 建立术语库
        tb1 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            tip="it is tb1",
            user=user1,
        )
        self.assertEqual(1, team1.term_banks().count())
        self.assertEqual(1, TermBank.objects.count())
        self.assertEqual(team1, tb1.team)
        self.assertEqual(user1, tb1.user)
        self.assertEqual(Language.by_code("zh-CN"), tb1.source_language)
        self.assertEqual(Language.by_code("ja"), tb1.target_language)
        self.assertEqual("tb1", tb1.name)
        self.assertEqual("it is tb1", tb1.tip)
        # == 开始测试 ==
        # == 没登录无法修改 ==
        data = self.put(
            f"/v1/term-banks/{str(tb1.id)}",
            json={
                "name": "tb2",
                "tip": "it is tb2",
                "source_language_id": str(Language.by_code("en").id),
                "target_language_id": str(Language.by_code("zh-TW").id),
            },
        )
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没权限修改 ==
        data = self.put(
            f"/v1/term-banks/{str(tb1.id)}",
            json={
                "name": "tb2",
                "tip": "it is tb2",
                "source_language_id": str(Language.by_code("en").id),
                "target_language_id": str(Language.by_code("zh-TW").id),
            },
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # == 目标语言和原语言不能相同 ==
        data = self.put(
            f"/v1/term-banks/{str(tb1.id)}",
            json={
                "name": "tb2",
                "tip": "it is tb2",
                "source_language_id": str(Language.by_code("en").id),
                "target_language_id": str(Language.by_code("en").id),
            },
            token=token1,
        )
        self.assertErrorEqual(data, TargetAndSourceLanguageSameError)
        # == 正常修改 ==
        data = self.put(
            f"/v1/term-banks/{str(tb1.id)}",
            json={
                "name": "tb2",
                "tip": "it is tb2",
                "source_language_id": str(Language.by_code("ja").id),
                "target_language_id": str(Language.by_code("en").id),
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        tb1.reload()
        self.assertEqual(1, team1.term_banks().count())
        self.assertEqual(1, TermBank.objects.count())
        self.assertEqual(team1, tb1.team)
        self.assertEqual(user1, tb1.user)
        self.assertEqual(Language.by_code("ja"), tb1.source_language)
        self.assertEqual(Language.by_code("en"), tb1.target_language)
        self.assertEqual("tb2", tb1.name)
        self.assertEqual("it is tb2", tb1.tip)
        # == user2可以修改自己的term bank，即使不在团队(没有修改权限) ==
        # 建立术语库
        tb2 = TermBank.create(
            name="user2tb",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            tip="",
            user=user2,
        )
        self.assertEqual("user2tb", tb2.name)
        data = self.put(
            f"/v1/term-banks/{str(tb2.id)}",
            json={
                "name": "user2tb2",
                "tip": "it is tb2",
                "source_language_id": str(Language.by_code("en").id),
                "target_language_id": str(Language.by_code("zh-TW").id),
            },
            token=token2,
        )
        self.assertErrorEqual(data)
        tb2.reload()
        self.assertEqual("user2tb2", tb2.name)

    def test_delete_term_bank(self):
        """测试删除术语库"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        # 建立术语库
        tb1 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            tip="it is tb1",
            user=user1,
        )
        self.assertEqual(1, team1.term_banks().count())
        self.assertEqual(1, TermBank.objects.count())
        self.assertEqual(team1, tb1.team)
        self.assertEqual(user1, tb1.user)
        self.assertEqual(Language.by_code("zh-CN"), tb1.source_language)
        self.assertEqual(Language.by_code("ja"), tb1.target_language)
        self.assertEqual("tb1", tb1.name)
        self.assertEqual("it is tb1", tb1.tip)
        # == 开始测试 ==
        # == 没登录无法删除 ==
        data = self.delete(f"/v1/term-banks/{str(tb1.id)}")
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没权限删除 ==
        data = self.delete(f"/v1/term-banks/{str(tb1.id)}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # == 正常删除 ==
        data = self.delete(f"/v1/term-banks/{str(tb1.id)}", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(0, team1.term_banks().count())
        self.assertEqual(0, TermBank.objects.count())
        with self.assertRaises(DoesNotExist):
            tb1.reload()
        # == user2可以删除自己的term bank，即使不在团队(没有删除权限) ==
        # 建立术语库
        tb2 = TermBank.create(
            name="user2tb",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            tip="",
            user=user2,
        )
        self.assertEqual("user2tb", tb2.name)
        self.assertEqual(1, team1.term_banks().count())
        data = self.delete(f"/v1/term-banks/{str(tb2.id)}", token=token2)
        self.assertErrorEqual(data)
        self.assertEqual(0, team1.term_banks().count())
        with self.assertRaises(DoesNotExist):
            tb2.reload()

    def test_get_term(self):
        """测试获取术语"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        # 建立术语库
        tb1 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user1,
        )
        # 建立术语
        Term.create(term_bank=tb1, source="s1", target="t1", tip="tb1", user=user1)
        # == 开始测试 ==
        # == 没有登录没有权限获取 ==
        data = self.get(f"/v1/term-banks/{str(tb1.id)}/terms")
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没有权限获取 ==
        data = self.get(f"/v1/term-banks/{str(tb1.id)}/terms", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # == 正常获取 ==
        data = self.get(f"/v1/term-banks/{str(tb1.id)}/terms", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual("s1", data.json[0]["source"])
        self.assertEqual("1", data.headers.get("X-Pagination-Count"))
        # == 通过word搜索 ==
        # 再给tb1创建一个术语
        Term.create(term_bank=tb1, source="s2", target="t2", tip="tb2", user=user2)
        # word=1
        data = self.get(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            query_string={"word": "1"},
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual("1", data.headers.get("X-Pagination-Count"))
        # word=T
        data = self.get(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            query_string={"word": "T"},
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual("2", data.headers.get("X-Pagination-Count"))

    def test_create_term(self):
        """测试创建术语"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        # 建立术语库
        tb1 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user1,
        )
        # == 没登录无法创建 ==
        data = self.post(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            json={"source": "s1", "tip": "it is tb1", "target": "t1"},
        )
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没权限创建 ==
        data = self.post(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            json={"source": "s1", "tip": "it is tb1", "target": "t1"},
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # == 正常创建 ==
        self.assertEqual(0, Term.objects.count())
        data = self.post(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            json={"source": "s1", "tip": "it is tb1", "target": "t1"},
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Term.objects.count())
        term1 = Term.objects.first()
        self.assertEqual("s1", term1.source)
        self.assertEqual("t1", term1.target)
        self.assertEqual("it is tb1", term1.tip)
        # == user2可以在自己创建的术语库中创建术语，即使没有权限 ==
        # 建立术语库
        tb2 = TermBank.create(
            name="tb2",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user2,
        )
        data = self.post(
            f"/v1/term-banks/{str(tb2.id)}/terms",
            json={"source": "s1", "tip": "it is tb1", "target": "t1"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, tb2.terms().count())

    def test_edit_term(self):
        """测试修改术语"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        # 建立术语库
        tb1 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user1,
        )
        # 正常创建
        self.assertEqual(0, Term.objects.count())
        data = self.post(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            json={"source": "s1", "tip": "it is tb1", "target": "t1"},
            token=token1,
        )
        self.assertEqual(1, Term.objects.count())
        term1 = Term.objects.first()
        self.assertEqual("s1", term1.source)
        self.assertEqual("t1", term1.target)
        self.assertEqual("it is tb1", term1.tip)
        # == 没登录无法修改 ==
        data = self.put(
            f"/v1/terms/{str(term1.id)}",
            json={"source": "s2", "tip": "it is tb2", "target": "t2"},
        )
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没权限修改 ==
        data = self.put(
            f"/v1/terms/{str(term1.id)}",
            json={"source": "s1", "tip": "it is tb2", "target": "t1"},
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # == 正常修改 ==
        data = self.put(
            f"/v1/terms/{str(term1.id)}",
            json={"source": "s2", "tip": "it is tb2", "target": "t2"},
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Term.objects.count())
        term1 = Term.objects.first()
        self.assertEqual("s2", term1.source)
        self.assertEqual("t2", term1.target)
        self.assertEqual("it is tb2", term1.tip)
        # == user2可以修改所属team bank或team是自己的team ==
        # == 修改team.user是自己的team ==
        # 在tb1中创建术语
        term2 = Term.create(term_bank=tb1, source="s", target="t", tip="t", user=user2)
        self.assertEqual("s", term2.source)
        data = self.put(
            f"/v1/terms/{str(term2.id)}",
            json={"source": "ss", "tip": "it is tb2", "target": "t2"},
            token=token2,
        )
        self.assertErrorEqual(data)
        term2.reload()
        self.assertEqual("ss", term2.source)
        # == 修改team_bank.user是自己的旗下team ==
        tb2 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user2,
        )
        # user1在tb2中创建术语
        term3 = Term.create(term_bank=tb2, source="s", target="t", tip="t", user=user1)
        self.assertEqual("s", term3.source)
        # user2可以修改
        data = self.put(
            f"/v1/terms/{str(term3.id)}",
            json={"source": "ss", "tip": "it is tb2", "target": "t2"},
            token=token2,
        )
        self.assertErrorEqual(data)
        term3.reload()
        self.assertEqual("ss", term3.source)

    def test_delete_term(self):
        """测试删除术语"""
        # == 准备工作 ==
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1", creator=user1)
        # 建立术语库
        tb1 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user1,
        )
        # 正常创建
        self.assertEqual(0, Term.objects.count())
        data = self.post(
            f"/v1/term-banks/{str(tb1.id)}/terms",
            json={"source": "s1", "tip": "it is tb1", "target": "t1"},
            token=token1,
        )
        self.assertEqual(1, Term.objects.count())
        term1 = Term.objects.first()
        self.assertEqual("s1", term1.source)
        self.assertEqual("t1", term1.target)
        self.assertEqual("it is tb1", term1.tip)
        # == 没登录无法删除 ==
        data = self.delete(f"/v1/terms/{str(term1.id)}")
        self.assertErrorEqual(data, NeedTokenError)
        # == user2没权限删除 ==
        data = self.delete(f"/v1/terms/{str(term1.id)}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # == 正常删除 ==
        data = self.delete(f"/v1/terms/{str(term1.id)}", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(0, Term.objects.count())
        with self.assertRaises(DoesNotExist):
            term1.reload()
        # == user2可以删除所属team bank或team是自己的team ==
        # == 删除team.user是自己的team ==
        # 在tb1中创建术语
        term2 = Term.create(term_bank=tb1, source="s", target="t", tip="t", user=user2)
        self.assertEqual("s", term2.source)
        self.assertEqual(1, Term.objects.count())
        data = self.delete(f"/v1/terms/{str(term2.id)}", token=token2)
        self.assertErrorEqual(data)
        self.assertEqual(0, Term.objects.count())
        with self.assertRaises(DoesNotExist):
            term2.reload()
        # == 删除team_bank.user是自己的旗下team ==
        tb2 = TermBank.create(
            name="tb1",
            team=team1,
            source_language=Language.by_code("zh-CN"),
            target_language=Language.by_code("ja"),
            user=user2,
        )
        # user1在tb2中创建术语
        term3 = Term.create(term_bank=tb2, source="s", target="t", tip="t", user=user1)
        self.assertEqual(1, Term.objects.count())
        # user2可以
        data = self.delete(f"/v1/terms/{str(term3.id)}", token=token2)
        self.assertErrorEqual(data)
        with self.assertRaises(DoesNotExist):
            term3.reload()
        self.assertEqual(0, Term.objects.count())
