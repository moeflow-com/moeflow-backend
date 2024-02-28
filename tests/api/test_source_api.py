from app.exceptions import (
    FileTypeNotSupportError,
    InvalidObjectIdError,
    NeedTokenError,
    NoPermissionError,
    SourceNotExistError,
)
from app.models.file import Source
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from flask_apikit.exceptions import ValidateError
from tests import MoeAPITestCase


class SourceAPITestCase(MoeAPITestCase):
    def test_get_sources(self):
        """测试获取文件的原文"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        target = project.targets().first()
        text_file = project.create_file("f1.txt")
        image_file = project.create_file("f1.jpg")
        # 创建原文
        image_file.create_source("1")
        image_file.create_source("2")
        image_file.create_source("3")
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
            # === 测试不分页的原文 ===
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                query_string={"target_id": str(target.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(3, len(data.json))
            # === 测试分页的原文 ===
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                query_string={"page": 2, "limit": 1, "target_id": str(target.id)},
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual(3, int(data.headers.get("X-Pagination-Count")))
            self.assertEqual(2, int(data.headers.get("X-Pagination-Page")))
            self.assertEqual(1, int(data.headers.get("X-Pagination-Limit")))
            self.assertEqual(3, int(data.headers.get("X-Pagination-Page-Count")))
            # === 测试不分页的原文 ===
            data = self.get(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                query_string={
                    "paging": "false",
                    "page": 2,
                    "limit": 1,
                    "target_id": str(target.id),
                },
            )
            self.assertErrorEqual(data)
            self.assertEqual(3, len(data.json))
            self.assertIsNone(data.headers.get("X-Pagination-Count"))
            self.assertIsNone(data.headers.get("X-Pagination-Page"))
            self.assertIsNone(data.headers.get("X-Pagination-Limit"))
            self.assertIsNone(data.headers.get("X-Pagination-Page-Count"))

    def test_create_image_sources(self):
        """测试创建原文【仅图片可用】"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        text_file = project.create_file("f1.txt")
        image_file = project.create_file("f1.jpg")
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能获取
            data = self.post("/v1/files/{}/sources".format(image_file.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能登录
            data = self.post("/v1/files/{}/sources".format(image_file.id), token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # 文件类型不能创建原文
            data = self.post("/v1/files/{}/sources".format(text_file.id), token=token)
            self.assertErrorEqual(data, FileTypeNotSupportError)
            # === 什么都不携带为空source ===
            data = self.post("/v1/files/{}/sources".format(image_file.id), token=token)
            self.assertErrorEqual(data)
            source = Source.by_id(data.json["id"])
            self.assertEqual("", source.content)
            self.assertEqual(0, source.x)
            self.assertEqual(0, source.y)
            self.assertEqual(1, source.position_type)
            # === 仅携带content ===
            data = self.post(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                json={"content": "con"},
            )
            self.assertErrorEqual(data)
            source = Source.by_id(data.json["id"])
            self.assertEqual("con", source.content)
            self.assertEqual(0, source.x)
            self.assertEqual(0, source.y)
            self.assertEqual(1, source.position_type)
            # === 仅携带x y ===
            data = self.post(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                json={"x": 0.1111111, "y": 0.666666},
            )
            self.assertErrorEqual(data)
            source = Source.by_id(data.json["id"])
            self.assertEqual("", source.content)
            self.assertEqual(0.1111111, source.x)
            self.assertEqual(0.666666, source.y)
            self.assertEqual(1, source.position_type)
            # === 仅携带 position_type ===
            data = self.post(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                json={"position_type": 2},
            )
            self.assertErrorEqual(data)
            source = Source.by_id(data.json["id"])
            self.assertEqual("", source.content)
            self.assertEqual(0, source.x)
            self.assertEqual(0, source.y)
            self.assertEqual(2, source.position_type)
            # === 完整的参数 ===
            data = self.post(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                json={
                    "content": "con",
                    "x": 0.1111111,
                    "y": 0.666666,
                    "position_type": 2,
                },
            )
            self.assertErrorEqual(data)
            source = Source.by_id(data.json["id"])
            self.assertEqual("con", source.content)
            self.assertEqual(0.1111111, source.x)
            self.assertEqual(0.666666, source.y)
            self.assertEqual(2, source.position_type)

    def test_edit_image_sources(self):
        """测试修改原文【仅图片可用】"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        text_file = project.create_file("f1.txt")
        image_file = project.create_file("f1.jpg")
        # 创建原文
        source = image_file.create_source("1")
        text_source = text_file.create_source("1")
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能获取
            data = self.put("/v1/sources/{}".format(source.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能登录
            data = self.put("/v1/sources/{}".format(source.id), token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # 文件类型不能创建原文
            data = self.put("/v1/sources/{}".format(text_source.id), token=token)
            self.assertErrorEqual(data, FileTypeNotSupportError)
            # 空json报错
            data = self.put("/v1/sources/{}".format(source.id), token=token)
            self.assertErrorEqual(data, ValidateError)
            # 类型不符报错
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"content": 2},
            )
            self.assertErrorEqual(data, ValidateError)
            # 类型不符报错
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"x": "dsfaa"},
            )
            self.assertErrorEqual(data, ValidateError)
            # 原文的初始化状态
            source.reload()
            self.assertEqual("1", source.content)
            self.assertEqual(0, source.x)
            self.assertEqual(0, source.y)
            self.assertEqual(1, source.position_type)
            # === 仅携带content ===
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"content": "con"},
            )
            self.assertErrorEqual(data)
            source.reload()
            self.assertEqual("con", source.content)
            self.assertEqual(0, source.x)
            self.assertEqual(0, source.y)
            self.assertEqual(1, source.position_type)
            # === 仅携带x y ===
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"x": 0.1111111, "y": 0.666666},
            )
            self.assertErrorEqual(data)
            source.reload()
            self.assertEqual("con", source.content)
            self.assertEqual(0.1111111, source.x)
            self.assertEqual(0.666666, source.y)
            self.assertEqual(1, source.position_type)
            # === 仅携带 position_type ===
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"position_type": 2},
            )
            self.assertErrorEqual(data)
            source.reload()
            self.assertEqual("con", source.content)
            self.assertEqual(0.1111111, source.x)
            self.assertEqual(0.666666, source.y)
            self.assertEqual(2, source.position_type)
            # === 完整的参数 ===
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"content": "", "x": 0.000, "y": 1.000, "position_type": 1},
            )
            self.assertErrorEqual(data)
            source.reload()
            self.assertEqual("", source.content)
            self.assertEqual(0, source.x)
            self.assertEqual(1, source.y)
            self.assertEqual(1, source.position_type)

    def test_delete_image_sources(self):
        """测试删除原文【仅图片可用】"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        text_file = project.create_file("f1.txt")
        image_file = project.create_file("f1.jpg")
        # 创建原文
        source = image_file.create_source("1")
        text_source = text_file.create_source("1")
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能获取
            data = self.delete("/v1/sources/{}".format(source.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能登录
            data = self.delete("/v1/sources/{}".format(source.id), token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # 文件类型不能删除原文
            data = self.delete("/v1/sources/{}".format(text_source.id), token=token)
            self.assertErrorEqual(data, FileTypeNotSupportError)
            # 初始状态
            source.reload()
            self.assertEqual(1, image_file.sources().count())
            self.assertEqual(1, text_file.sources().count())
            # === 删除 ===
            data = self.delete("/v1/sources/{}".format(source.id), token=token)
            self.assertErrorEqual(data)
            self.assertEqual(0, image_file.sources().count())
            self.assertEqual(1, text_file.sources().count())

    def test_edit_image_source_rank(self):
        """测试修改原文排序【仅图片可用】"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        text_file = project.create_file("f1.txt")
        image_file = project.create_file("f1.jpg")
        # 创建原文
        source1 = image_file.create_source("1")
        source2 = image_file.create_source("2")
        source3 = image_file.create_source("3")
        text_source = text_file.create_source("1")
        with self.app.test_request_context():
            # === 错误测试 ===
            # 没登录不能获取
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                json={"next_source_id": "end"},
            )
            self.assertErrorEqual(data, NeedTokenError)
            # 其他用户不能登录
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                token=token2,
                json={"next_source_id": "end"},
            )
            self.assertErrorEqual(data, NoPermissionError)
            # 文件类型不能创建原文
            data = self.put(
                "/v1/sources/{}/rank".format(text_source.id),
                token=token,
                json={"next_source_id": "end"},
            )
            self.assertErrorEqual(data, FileTypeNotSupportError)
            # 空json报错
            data = self.put("/v1/sources/{}/rank".format(source1.id), token=token)
            self.assertErrorEqual(data, ValidateError)
            # 类型不符报错
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                token=token,
                json={"next_source_id": 2},
            )
            self.assertErrorEqual(data, ValidateError)
            # 类型不符报错
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                token=token,
                json={"next_source_id": "12312"},
            )
            self.assertErrorEqual(data, InvalidObjectIdError)
            # 未找到原文件
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                token=token,
                json={"next_source_id": "5bfce445ff036b1b86666666"},
            )
            self.assertErrorEqual(data, SourceNotExistError)
            # 原文的初始化状态
            source1.reload()
            source2.reload()
            source3.reload()
            self.assertEqual(0, source1.rank)
            self.assertEqual(1, source2.rank)
            self.assertEqual(2, source3.rank)
            # === 移动到某个之前 ===
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                token=token,
                json={"next_source_id": str(source3.id)},
            )
            self.assertErrorEqual(data)
            source1.reload()
            source2.reload()
            source3.reload()
            self.assertEqual(0, source2.rank)
            self.assertEqual(1, source1.rank)
            self.assertEqual(2, source3.rank)
            # === 移动到end ===
            data = self.put(
                "/v1/sources/{}/rank".format(source1.id),
                token=token,
                json={"next_source_id": "end"},
            )
            self.assertErrorEqual(data)
            source1.reload()
            source2.reload()
            source3.reload()
            self.assertEqual(0, source2.rank)
            self.assertEqual(1, source3.rank)
            self.assertEqual(2, source1.rank)

    def test_position_type_limit(self):
        """测试 position_type 必须为框内:1 框外:2"""
        # === 创建测试数据 ===
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        User.objects(email="2@2.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        image_file = project.create_file("f1.jpg")
        # 创建原文
        source = image_file.create_source("1")
        with self.app.test_request_context():
            # 修改
            data = self.put(
                "/v1/sources/{}".format(source.id),
                token=token,
                json={"position_type": 3},
            )
            self.assertErrorEqual(data, ValidateError)
            # 创建
            data = self.post(
                "/v1/files/{}/sources".format(image_file.id),
                token=token,
                json={"position_type": 3},
            )
            self.assertErrorEqual(data, ValidateError)
