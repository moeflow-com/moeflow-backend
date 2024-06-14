from app.models.file import File
from app.models.project import Project
import json
from unittest import TestCase

import os
from mongoengine import connection

from app import create_app, FILE_PATH
from app.factory import init_db
from app.models.site_setting import SiteSetting
from app.models.user import User
from app.models.team import Team
from app.models.project import ProjectSet
from app.models.v_code import VCodeType, VCode
from typing import Any, Union

TEST_FILE_PATH = os.path.abspath(os.path.join(FILE_PATH, "test"))
DEFAULT_TEAMS_COUNT = 1
DEFAULT_TEAM_USER_RELATIONS = 1
DEFAULT_PROJECT_SETS_COUNT = 1
DEFAULT_USERS_COUNT = 1


def create_test_app():
    # 先创建app连接上数据库
    app = create_app()
    # 不是_test结尾则停止测试,防止数据覆盖
    if not connection.get_db().name.endswith("_test"):
        raise AssertionError("Please use *_test database")
    # reset the db
    connection.get_db().client.drop_database(connection.get_db().name)
    init_db(app)
    return app


class MoeTestCase(TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)
        self.disable_whitelist()
        self.disable_only_allow_admin_create_team()

    def tearDown(self):
        self.app_context.pop()

    def create_user(self, name: str, email=None, password="123456") -> User:
        """创建测试用户"""
        if email is None:
            email = name + "@test.com"
        user = User.create(name=name, email=email, password=password)
        return user

    def create_team(self, name: str, **kwargs) -> Team:
        """创建测试团队"""
        user = self.create_user(name + "-creator")
        team = Team.create(name, creator=user, **kwargs)
        return team

    def create_project_set(self, name: str, **kwargs) -> ProjectSet:
        """创建测试项目集"""
        team = self.create_team(name + "-team")
        project_set = ProjectSet.create(name, team=team, **kwargs)
        return project_set

    def create_project(self, name: str, **kwargs) -> Project:
        """创建测试项目"""
        project_set = self.create_project_set(name + "-project_set")
        user = self.get_creator(project_set.team)
        project = Project.create(
            name, project_set.team, project_set=project_set, creator=user, **kwargs
        )
        return project

    def create_file(self, name: str, **kwargs) -> File:
        """创建测试文件"""
        project = self.create_project(name + "-project")
        file = project.create_file(name)
        return file

    def get_creator(self, group: Union[Team, Project]) -> User:
        """获取团队或项目的创建人"""
        return group.users(role=group.role_cls.by_system_code("creator")).first()

    def disable_whitelist(self):
        """禁用白名单"""
        site_setting = SiteSetting.get()
        site_setting.enable_whitelist = False
        site_setting.save()

    def disable_only_allow_admin_create_team(self):
        """禁用仅允许管理员创建团队"""
        site_setting = SiteSetting.get()
        site_setting.only_allow_admin_create_team = False
        site_setting.save()


class MoeAPITestCase(MoeTestCase):
    def assertErrorEqual(self, resp, error=None):
        """
        检测api返回的错误码与定义的错误是否相同
        不同时,同时打印错误api返回的信息

        :param data:
        :param error: 没有则认为error.code=0
        :return:
        """
        # 期望没有错误
        if error is None:
            if not (200 <= resp.status_code <= 299):
                raise AssertionError(
                    f"\n== 期望没有错误，却返回了错误 ==\n"
                    f"Status Code: {resp.status_code} # 应介于200-299\n"
                    f"Data: {resp.json}"
                )
            if resp.status_code == 204:
                return  # 如果是204，无返回内容，则不检查json中code
            if isinstance(resp.json, list):
                return  # 数组不检查json中code
            if resp.json.get("code"):
                raise AssertionError(
                    f"\n== 期望没有错误，却返回了错误 ==\n"
                    f"Expected : 无错误\n"
                    f"Actual   : {resp.json}"
                )
        else:
            if not (400 <= resp.status_code <= 499):
                raise AssertionError(
                    f"\n== 期望有错误，却没有返回错误 ==\n"
                    f"Status Code: {resp.status_code} # 应介于400-499\n"
                    f"Data: {resp.json}"
                )
            if error.code != resp.json.get("code"):
                raise AssertionError(
                    f"\n== 接口返回错误与期望错误不匹配 ==\n"
                    f"Expected : {error.code}\n"
                    f"Actual   : {resp.json.get('code')} ({resp.json})"
                )

    def open(self, *args, **kwargs):
        # 查看是否指定client
        client = kwargs.pop("client", None)
        if client is None:
            client = self.client
        # 增加headers
        if kwargs.get("headers") is None:
            kwargs["headers"] = {
                # 默认增加跨域参数
                "Origin": "https://example.com",
            }
        # 如果给予data参数，则转换为json，并设置json内容头
        json_data = kwargs.pop("json", None)
        if isinstance(json_data, dict):
            kwargs["data"] = json.dumps(json_data)
            kwargs["headers"]["Content-Type"] = "application/json"
        token = kwargs.pop("token", None)
        if token:
            kwargs["headers"]["Authorization"] = "Bearer {}".format(token)
        resp: Any = client.open(*args, **kwargs)
        # 如果没有json，则返回内容
        if resp.json is None and resp.status_code != 204:
            raise AssertionError(
                "Response is not JSON\n"
                + "=" * 60
                + "\n"
                + resp.get_data(as_text=True)
                + "\n"
                + "=" * 60
            )
        return resp

    def get(self, *args, **kw):
        kw["method"] = "GET"
        return self.open(*args, **kw)

    def patch(self, *args, **kw):
        kw["method"] = "PATCH"
        return self.open(*args, **kw)

    def post(self, *args, **kw):
        kw["method"] = "POST"
        return self.open(*args, **kw)

    def head(self, *args, **kw):
        kw["method"] = "HEAD"
        return self.open(*args, **kw)

    def put(self, *args, **kw):
        kw["method"] = "PUT"
        return self.open(*args, **kw)

    def delete(self, *args, **kw):
        kw["method"] = "DELETE"
        return self.open(*args, **kw)

    def options(self, *args, **kw):
        kw["method"] = "OPTIONS"
        return self.open(*args, **kw)

    def trace(self, *args, **kw):
        kw["method"] = "TRACE"
        return self.open(*args, **kw)

    def get_captcha(self):
        """通过API获取一个人机验证码"""
        # 申请人机验证码
        data = self.post("/v1/captchas")
        self.assertErrorEqual(data)
        self.assertIn("info", data.json)
        self.assertIn("image", data.json)
        # 获取人机验证码内容
        captcha = VCode.objects(type=VCodeType.CAPTCHA, info=data.json["info"]).first()[
            "content"
        ]
        # 返回captcha_info和captcha
        return data.json["info"], captcha
