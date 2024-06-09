from app.exceptions import NeedTokenError, NoPermissionError
from app.models.file import Translation
from app.models.project import Project, ProjectRole
from app.models.team import Team
from app.models.user import User
from tests import MoeAPITestCase
from flask_apikit.exceptions import ValidateError


class TranslationAPITestCase(MoeAPITestCase):
    def test_get_translations(self):
        """测试获取原文的翻译，使用的file的sources接口"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        target = project.targets().first()
        image_file = project.create_file("f1.jpg")
        # 创建原文
        source = image_file.create_source("1")
        source.create_translation("t1", target, user=user)
        source.create_translation("t2", target, user=user2)
        with self.app.test_request_context():
            # === 权限测试 ===
            # 没登录不能获取
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                query_string={"target_id": str(target.id)},
            )
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能登录
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                query_string={"target_id": str(target.id)},
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # === 测试用户1获取 ===
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                query_string={"target_id": str(target.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual(1, len(data.json[0]["translations"]))
            self.assertEqual("t1", data.json[0]["my_translation"]["content"])
            # === 测试用户2获取 ===
            user2.join(project)
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                query_string={"target_id": str(target.id)},
                token=token2,
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual(1, len(data.json[0]["translations"]))
            self.assertEqual("t2", data.json[0]["my_translation"]["content"])

    def test_create_translation(self):
        """测试创建翻译"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        file = project.create_file("f1.txt")
        source = file.create_source("原文")
        target = project.targets().first()
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能创建
            data = self.post("/v1/sources/{}/translations".format(source.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能创建
            data = self.post(
                "/v1/sources/{}/translations".format(source.id), token=token2
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 空参数
            data = self.post(
                "/v1/sources/{}/translations".format(source.id), json={}, token=token
            )
            self.assertErrorEqual(data, ValidateError)
            # === 完整的参数 ===
            data = self.post(
                "/v1/sources/{}/translations".format(source.id),
                token=token,
                json={"content": "yw", "target_id": str(target.id)},
            )
            self.assertErrorEqual(data)
            # 将user2加入
            user2.join(project)
            # user2能创建了
            data = self.post(
                "/v1/sources/{}/translations".format(source.id),
                token=token2,
                json={"content": "yw2", "target_id": str(target.id)},
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, Translation.objects().count())
            self.assertCountEqual(
                ["yw", "yw2"], [t.content for t in Translation.objects()]
            )
            # === user再次创建，仅会修改自己的翻译 ===
            data = self.post(
                "/v1/sources/{}/translations".format(source.id),
                token=token,
                json={"content": "yw1", "target_id": str(target.id)},
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, Translation.objects().count())
            self.assertCountEqual(
                ["yw1", "yw2"], [t.content for t in Translation.objects()]
            )

    def test_edit_translation(self):
        """测试修改翻译"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        translator_token = self.create_user("22", "2@2.com", "111111").generate_token()
        translator = User.objects(email="2@2.com").first()  # 翻译者
        proofreader_token = self.create_user("33", "3@3.com", "111111").generate_token()
        proofreader = User.objects(email="3@3.com").first()  # 校对者
        token2 = self.create_user("44", "4@4.com", "111111").generate_token()
        User.objects(email="4@4.com").first()  # 其他用户
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        target = project.targets().first()
        file = project.create_file("f1.txt")
        source = file.create_source("原文")
        translation = source.create_translation("yw", target, user=translator)
        # 加入用户
        translator.join(project, ProjectRole.by_system_code("translator"))
        proofreader.join(project, ProjectRole.by_system_code("proofreader"))
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能修改
            data = self.put("/v1/translations/{}".format(translation.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能修改
            data = self.put(
                "/v1/translations/{}".format(translation.id),
                token=token2,
                json={"content": "yw-user2"},
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 校对不能修改他人原文
            data = self.put(
                "/v1/translations/{}".format(translation.id),
                token=proofreader_token,
                json={"content": "yw-pro"},
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 翻译者不能校对
            data = self.put(
                "/v1/translations/{}".format(translation.id),
                token=translator_token,
                json={"proofread_content": "yw-tra"},
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 翻译者不能select
            data = self.put(
                "/v1/translations/{}".format(translation.id),
                token=translator_token,
                json={"selected": "true"},
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 空json报错
            data = self.put(
                "/v1/translations/{}".format(translation.id), json={}, token=token
            )
            self.assertErrorEqual(data, ValidateError)
            # 翻译的初始化状态
            translation.reload()
            self.assertEqual("yw", translation.content)
            self.assertEqual(translator, translation.user)
            self.assertEqual("", translation.proofread_content)
            self.assertEqual(None, translation.proofreader)
            self.assertEqual(False, translation.selected)
            self.assertEqual(None, translation.selector)
            # === 自己可以修改content ===
            data = self.put(
                "/v1/translations/{}".format(translation.id),
                token=translator_token,
                json={"content": "yw-tra"},
            )
            self.assertErrorEqual(data)
            translation.reload()
            self.assertEqual("yw-tra", translation.content)
            self.assertEqual(translator, translation.user)
            self.assertEqual("", translation.proofread_content)
            self.assertEqual(None, translation.proofreader)
            self.assertEqual(False, translation.selected)
            self.assertEqual(None, translation.selector)
            # === 校对者可以校对和选定 ===
            data = self.put(
                "/v1/translations/{}".format(translation.id),
                token=proofreader_token,
                json={"proofread_content": "pc", "selected": "true"},
            )
            self.assertErrorEqual(data)
            translation.reload()
            self.assertEqual("yw-tra", translation.content)
            self.assertEqual(translator, translation.user)
            self.assertEqual("pc", translation.proofread_content)
            self.assertEqual(proofreader, translation.proofreader)
            self.assertEqual(True, translation.selected)
            self.assertEqual(proofreader, translation.selector)

    def test_delete_translation(self):
        # === 创建测试数据 ===
        self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        translator_token = self.create_user("22", "2@2.com", "111111").generate_token()
        translator = User.objects(email="2@2.com").first()  # 翻译者
        proofreader_token = self.create_user("33", "3@3.com", "111111").generate_token()
        proofreader = User.objects(email="3@3.com").first()  # 校对者
        token2 = self.create_user("44", "4@4.com", "111111").generate_token()
        User.objects(email="4@4.com").first()  # 其他用户
        coordinator_token = self.create_user("55", "5@5.com", "111111").generate_token()
        coordinator = User.objects(email="5@5.com").first()  # 其他用户
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        target = project.targets().first()
        file = project.create_file("f1.txt")
        source = file.create_source("原文")
        translation = source.create_translation("yw", target, user=translator)
        # 加入用户
        translator.join(project, ProjectRole.by_system_code("translator"))
        proofreader.join(project, ProjectRole.by_system_code("proofreader"))
        coordinator.join(project, ProjectRole.by_system_code("coordinator"))
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能删除
            data = self.delete("/v1/translations/{}".format(translation.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能修改
            data = self.delete(
                "/v1/translations/{}".format(translation.id), token=token2
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 校对不能删除他人原文
            data = self.delete(
                "/v1/translations/{}".format(translation.id),
                token=proofreader_token,
            )
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(1, Translation.objects().count())
            # 可以删除自己的译文
            data = self.delete(
                "/v1/translations/{}".format(translation.id),
                token=translator_token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(0, Translation.objects().count())
            # 再创建一个译文
            translation = source.create_translation("yw", target, user=translator)
            self.assertEqual(1, Translation.objects().count())
            # 协调者可以删除他人译文
            data = self.delete(
                "/v1/translations/{}".format(translation.id),
                token=coordinator_token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(0, Translation.objects().count())
