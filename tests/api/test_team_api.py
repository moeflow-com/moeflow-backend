from mongoengine import DoesNotExist

from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.exceptions import (
    NeedTokenError,
    NoPermissionError,
    RequestDataEmptyError,
    UserNotExistError,
    CreatorCanNotLeaveError,
    RoleNotExistError,
    ProjectNotExistError,
)
from app.exceptions.team import OnlyAllowAdminCreateTeamError
from app.models.project import Project, ProjectSet
from app.models.site_setting import SiteSetting
from app.models.team import Team
from app.models.user import User
from app.constants.project import ProjectStatus
from app.constants.role import RoleType
from flask_apikit.exceptions import ValidateError
from tests import MoeAPITestCase


class TeamAPITestCase(MoeAPITestCase):
    def test_get_team_list(self):
        """
        测试获取团队列表，是否正确的返回了 joined 值
        """
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            member_role = Team.role_cls.by_system_code("beginner")
            # user1 正确创建team1
            data = self.post(
                "/v1/teams",
                json={
                    "name": "t1",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            # user2 正确创建team2
            data = self.post(
                "/v1/teams",
                json={
                    "name": "t2",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token2,
            )
            self.assertErrorEqual(data)

            # user1 获取团队
            # team1 加入的
            data = self.get(f"/v1/teams", query_string={"word": "t1"}, token=token)
            self.assertErrorEqual(data)
            self.assertTrue(data.json[0]["joined"])
            # team2 未加入
            data = self.get(f"/v1/teams", query_string={"word": "t2"}, token=token)
            self.assertErrorEqual(data)
            self.assertFalse(data.json[0]["joined"])

            # user2 获取团队
            # team1 未加入
            data = self.get(f"/v1/teams", query_string={"word": "t1"}, token=token2)
            self.assertErrorEqual(data)
            self.assertFalse(data.json[0]["joined"])
            # team2 加入的
            data = self.get(f"/v1/teams", query_string={"word": "t2"}, token=token2)
            self.assertErrorEqual(data)
            self.assertTrue(data.json[0]["joined"])

    def test_get_team_list2(self):
        """
        测试获取团队列表
        1. 没有 word 值时不能获取
        2. 获取数量正确
        """
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            member_role = Team.role_cls.by_system_code("beginner")
            # user1 正确创建team1
            data = self.post(
                "/v1/teams",
                json={
                    "name": "t1",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            # user1 正确创建team2
            data = self.post(
                "/v1/teams",
                json={
                    "name": "t2",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            # 没有 word，报错
            data = self.get(f"/v1/teams", token=token)
            self.assertErrorEqual(data, RequestDataEmptyError)
            # word = t，搜到 2 个
            data = self.get(f"/v1/teams", query_string={"word": "t"}, token=token)
            self.assertErrorEqual(data)
            self.assertEqual(2, len(data.json))
            # word = 1，搜到 1 个
            data = self.get(f"/v1/teams", query_string={"word": "1"}, token=token)
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))

    def test_get_team(self):
        """
        测试获取团队
        """
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            self.create_user("22", "2@1.com", "111111").generate_token()
            member_role = Team.role_cls.by_system_code("beginner")
            # 正确创建team1
            data = self.post(
                "/v1/teams",
                json={
                    "name": "t1",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            # 使用接口（通过返回的 team.id）获取这个团队
            data = self.get(f'/v1/teams/{data.json["team"]["id"]}', token=token)
            self.assertErrorEqual(data)
            self.assertEqual("t1", data.json["name"])

    def test_create_team(self):
        """
        测试了如下用例：
        没有登录时，不能创建
        缺少名称字段时，不能创建
        名称长度错误时，不能创建
        正确的创建
        与其他团队重名时，不能创建
        默认角色使用其他团队的角色，不能创建
        """
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            # == 没有登录时，不能创建 ==
            data = self.post("/v1/teams", json={"name": "t1"})
            self.assertErrorEqual(data, NeedTokenError)
            # == 缺少名称字段时，不能创建 ==
            data = self.post("/v1/teams", token=token)
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("name"))
            # == 名称长度错误时，不能创建 ==
            data = self.post("/v1/teams", json={"name": "1"}, token=token)
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("name"))
            # == 正确的创建 ==
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 正确创建team1
            data = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            # 检测有一个团队
            self.assertEqual(Team.objects.count(), 1)
            # 获得这个团队
            team = Team.objects(name="11").first()
            # 已加入，并且是创建人
            self.assertEqual(1, len(team.users()))
            self.assertEqual(user, team.users()[0])
            self.assertEqual("creator", team.users()[0].get_role(team).system_code)
            # == 与其他团队重名时，不能创建 ==
            # 创建team2，无法创建同名团队
            data = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("name"))
            # 创建team2，其他名字可以，这时候有两个团队
            data = self.post(
                "/v1/teams",
                json={
                    "name": "22",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            # 检测有两个团队
            self.assertEqual(2, Team.objects.count())
            # == 默认角色使用其他团队的角色，不能创建 ==
            # 给team1创建一个role
            custom_role = team.create_role(
                name="custom_role",
                level=1,
                permissions=[Team.permission_cls.ACCESS],
                intro="It is custom role",
            )
            self.assertEqual(1, team.roles(type=RoleType.CUSTOM).count())
            # 创建team3，使用team1的role，会报验证错误
            data = self.post(
                "/v1/teams",
                json={
                    "name": "33",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(custom_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("default_role"))

    def test_edit_team(self):
        """
        测试修改团队，有如下用例：
        没有登录时，无法修改
        没有权限，无法修改
        name长度过短，无法修改
        空json报错
        name长度过短，无法修改
        和其他团队名称重复，无法修改
        使用其他团队的角色作为默认角色，无法修改
        正确的修改（不改名）
        正确的修改（改名，改默认角色）
        没有name和default_role参数，可以修改其他部分
        仅修改default_role参数
        """
        with self.app.test_request_context():
            # 创建用户
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            # 创建一个team
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 创建team1
            data1 = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data1)
            # 创建team2
            data2 = self.post(
                "/v1/teams",
                json={
                    "name": "22",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data2)
            # 检测有两个团队
            self.assertEqual(Team.objects.count(), 2)
            # 获得团队
            team1 = Team.objects(id=data1.json["team"]["id"]).first()
            team2 = Team.objects(id=data2.json["team"]["id"]).first()
            # == 没有登录，无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
            )
            self.assertErrorEqual(data, NeedTokenError)
            # == 没有权限，无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == name长度过短，无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}",
                json={
                    "name": "",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("name"))
            # == 空json报错 ==
            data = self.put(f"/v1/teams/{str(team1.id)}", token=token)
            self.assertErrorEqual(data, RequestDataEmptyError)
            data = self.put(f"/v1/teams/{str(team1.id)}", json={}, token=token)
            self.assertErrorEqual(data, RequestDataEmptyError)
            # == 错误的名称会被过滤 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}", json={"_name": ""}, token=token
            )
            self.assertErrorEqual(data, RequestDataEmptyError)
            # == 和其他team名称重复，无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}",
                json={
                    "name": "22",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("name"))
            # == 使用其他团队的角色作为默认角色，无法修改 ==
            # 给team2创建一个role
            custom_role = team2.create_role(
                name="custom_role",
                level=1,
                permissions=[Team.permission_cls.ACCESS],
                intro="It is custom role",
            )
            data = self.put(
                f"/v1/teams/{str(team1.id)}",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(custom_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            self.assertIsNotNone(data.json["message"].get("default_role"))
            # == 正确的修改（不改名） ==
            self.assertEqual("22", team2.name)
            self.assertEqual(AllowApplyType.NONE, team2.allow_apply_type)
            self.assertEqual(
                ApplicationCheckType.ADMIN_CHECK, team2.application_check_type
            )
            self.assertEqual(member_role, team2.default_role)
            self.assertEqual("", team2.intro)
            data = self.put(
                f"/v1/teams/{str(team2.id)}",
                json={
                    "name": "22",
                    "allow_apply_type": AllowApplyType.ALL,
                    "application_check_type": ApplicationCheckType.NO_NEED_CHECK,  # noqa: E501
                    "default_role": str(member_role.id),
                    "intro": "22",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            team2.reload()
            self.assertEqual("22", team2.name)
            self.assertEqual(AllowApplyType.ALL, team2.allow_apply_type)
            self.assertEqual(
                ApplicationCheckType.NO_NEED_CHECK,
                team2.application_check_type,
            )
            self.assertEqual(member_role, team2.default_role)
            self.assertEqual("22", team2.intro)
            # == 正确的修改（改名，改默认角色） ==
            data = self.put(
                f"/v1/teams/{str(team2.id)}",
                json={
                    "name": "33",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.NO_NEED_CHECK,  # noqa: E501
                    "default_role": str(custom_role.id),
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            team2.reload()
            self.assertEqual("33", team2.name)
            self.assertEqual(AllowApplyType.NONE, team2.allow_apply_type)
            self.assertEqual(
                ApplicationCheckType.NO_NEED_CHECK,
                team2.application_check_type,
            )
            self.assertEqual(custom_role, team2.default_role)
            self.assertEqual("", team2.intro)
            # == 没有name和default_role参数，可以修改其他部分 ==
            data = self.put(
                f"/v1/teams/{str(team2.id)}",
                json={
                    "allow_apply_type": AllowApplyType.ALL,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "intro": "1",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            team2.reload()
            self.assertEqual("33", team2.name)
            self.assertEqual(AllowApplyType.ALL, team2.allow_apply_type)
            self.assertEqual(
                ApplicationCheckType.ADMIN_CHECK, team2.application_check_type
            )
            self.assertEqual(custom_role, team2.default_role)
            self.assertEqual("1", team2.intro)
            # == 仅修改default_role参数 ==
            data = self.put(
                f"/v1/teams/{str(team2.id)}",
                json={"default_role": str(member_role.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            team2.reload()
            self.assertEqual("33", team2.name)
            self.assertEqual(AllowApplyType.ALL, team2.allow_apply_type)
            self.assertEqual(
                ApplicationCheckType.ADMIN_CHECK, team2.application_check_type
            )
            self.assertEqual(member_role, team2.default_role)
            self.assertEqual("1", team2.intro)

    def test_delete_team(self):
        """
        测试删除团队，有如下用例：
        未登录，无法删除
        没有权限，无法删除
        有进行中的项目的团队，无法删除
        """
        with self.app.test_request_context():
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            user1 = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            # 创建一个team
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 创建team1
            data1 = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token1,
            )
            self.assertErrorEqual(data1)
            # 创建team2
            data2 = self.post(
                "/v1/teams",
                json={
                    "name": "22",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token1,
            )
            self.assertErrorEqual(data2)
            # 检测有两个团队
            self.assertEqual(Team.objects.count(), 2)
            # 获得团队
            team1 = Team.objects(id=data1.json["team"]["id"]).first()
            team2 = Team.objects(id=data2.json["team"]["id"]).first()
            # == 未登录，无法删除 ==
            data = self.delete(f"/v1/teams/{str(team1.id)}")
            self.assertErrorEqual(data, NeedTokenError)
            # == 没有权限，无法删除 ==
            data = self.delete(f"/v1/teams/{str(team1.id)}", token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 有进行中的项目的团队无法删除 ==
            # 给team1，team2创建进行中的项目
            project1 = Project.create(name="p1", team=team1, creator=user1)
            Project.create(name="p1", team=team2, creator=user1)
            self.assertEqual(1, team1.projects().count())
            self.assertEqual(1, team2.projects().count())
            self.assertEqual(2, Project.objects.count())
            data = self.delete(f"/v1/teams/{str(team1.id)}", token=token1)
            self.assertErrorEqual(data, NoPermissionError)
            # 将team1的项目完结，然后删除
            project1.plan_finish()
            project1.finish()
            data = self.delete(f"/v1/teams/{str(team1.id)}", token=token1)
            self.assertErrorEqual(data)
            self.assertEqual(1, team2.projects().count())
            self.assertEqual(1, Project.objects.count())

    def test_get_team_users(self):
        """
        测试获取用户列表，有如下用例：
        非团队成员无法访问
        使用 word 限制搜索
        返回的 role 是否正确
        """
        with self.app.test_request_context():
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            user1 = User.objects(email="1@1.com").first()  # creator
            token2 = self.create_user("22", "2@2.com", "222222").generate_token()
            user2 = User.objects(email="2@2.com").first()  # senior
            token3 = self.create_user("33", "3@3.com", "333333").generate_token()
            User.objects(email="3@3.com").first()  # 非团队成员
            # 创建team1
            team1 = Team.create(name="t1", creator=user1)
            senior_role = Team.role_cls.by_system_code("senior")
            user2.join(team1, role=senior_role)
            # == 非团队成员无法访问 ==
            data = self.get(f"/v1/teams/{str(team1.id)}/users", token=token3)
            self.assertErrorEqual(data, NoPermissionError)
            # == 使用 word 限制搜索 ==
            # == 返回的 role 是否正确 ==
            # 获取 2 个
            data = self.get(f"/v1/teams/{str(team1.id)}/users", token=token1)
            self.assertErrorEqual(data)
            self.assertEqual(2, len(data.json))
            # 单独获取用户 11
            data = self.get(f"/v1/teams/{str(team1.id)}/users?word=1", token=token2)
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual("creator", data.json[0]["role"]["system_code"])
            # 单独获取用户 22
            data = self.get(f"/v1/teams/{str(team1.id)}/users?word=2", token=token2)
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual("senior", data.json[0]["role"]["system_code"])

    def test_edit_team_user(self):
        """
        测试修改团队用户角色，有如下用例：
        “非团队成员”不能修改角色
        “管理员”不能修改“非团队成员”角色
        “成员”不能修改“见习成员”角色（没有权限）
        “管理员”不能修改“管理员”角色（等级一样）
        “管理员”不能修改“创建者”角色（等级低）
        “管理员”不能修改成员为“管理员”角色（等级一样）
        “管理员”不能修改成员为“创建者”角色（等级低）
        “管理员”可以修改成员为“见习成员”角色
        可以使用自定义角色
        不能使用不存在的自定义角色
        不能使用其他团队的自定义角色
        """
        with self.app.test_request_context():
            # 创建用户
            self.create_user("11", "1@1.com", "111111").generate_token()
            user1 = User.objects(email="1@1.com").first()  # 见习成员
            self.create_user("22", "2@2.com", "222222").generate_token()
            user2 = User.objects(email="2@2.com").first()  # 成员
            token3 = self.create_user("33", "3@3.com", "333333").generate_token()
            user3 = User.objects(email="3@3.com").first()  # 资深成员
            token4 = self.create_user("44", "4@4.com", "444444").generate_token()
            user4 = User.objects(email="4@4.com").first()  # 管理员
            self.create_user("442", "42@4.com", "444444").generate_token()
            user4_2 = User.objects(email="42@4.com").first()  # 管理员2
            self.create_user("55", "5@5.com", "555555").generate_token()
            user5 = User.objects(email="5@5.com").first()  # 创建者
            token6 = self.create_user("66", "6@6.com", "666666").generate_token()
            user6 = User.objects(email="6@6.com").first()  # 非团队成员
            # 创建team1
            team1 = Team.create(name="t1", creator=user5)
            team2 = Team.create(name="t2")
            beginner_role = Team.role_cls.by_system_code("beginner")
            member_role = Team.role_cls.by_system_code("member")
            senior_role = Team.role_cls.by_system_code("senior")
            admin_role = Team.role_cls.by_system_code("admin")
            creator_role = Team.role_cls.by_system_code("creator")
            user1.join(team1, role=beginner_role)
            user2.join(team1, role=member_role)
            user3.join(team1, role=senior_role)
            user4.join(team1, role=admin_role)
            user4_2.join(team1, role=admin_role)
            # 创建自定义角色
            role1 = team1.create_role("t1r", 0, permissions=[1])
            role2 = team2.create_role("t2r", 0, permissions=[1])
            # == “非团队成员”不能修改角色 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user1.id)}",
                json={"role": str(member_role.id)},
                token=token6,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改“非团队成员”角色 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user6.id)}",
                json={"role": str(member_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, UserNotExistError)
            # == “资深成员”不能修改“见习成员”角色（没有权限） ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user1.id)}",
                json={"role": str(member_role.id)},
                token=token3,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改“管理员”角色（等级一样） ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user4_2.id)}",
                json={"role": str(member_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改“创建者”角色（等级低） ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user5.id)}",
                json={"role": str(member_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改成员为“管理员”角色（等级一样） ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                json={"role": str(admin_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改成员为“创建者”角色（等级低） ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                json={"role": str(creator_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”可以修改“成员”为“见习成员”角色 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                json={"role": str(beginner_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data)
            user2.reload()
            self.assertEqual(beginner_role, user2.get_role(team1))
            # == 可以使用自定义角色 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                json={"role": str(role1.id)},
                token=token4,
            )
            self.assertErrorEqual(data)
            user2.reload()
            self.assertEqual(role1, user2.get_role(team1))
            # == 不能使用其他团队的自定义角色 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                json={"role": str(role2.id)},
                token=token4,
            )
            self.assertErrorEqual(data, RoleNotExistError)
            user2.reload()
            self.assertEqual(role1, user2.get_role(team1))  # 仍然是 role1
            # == 不能使用不存在的自定义角色 ==
            data = self.put(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                json={"role": "5e86e6303fb2000000000000"},
                token=token4,
            )
            self.assertErrorEqual(data, RoleNotExistError)
            user2.reload()
            self.assertEqual(role1, user2.get_role(team1))  # 仍然是 role1

    def test_delete_team_user(self):
        """
        测试删除团队用户，有如下用例：
        资深成员无法删除成员
        资深成员无法删除管理员
        管理员无法删除管理员
        管理员无法删除非团队成员
        非团队成员无法删除成员
        成员可以删除自己
        管理员可以删除资深成员
        管理员可以删除自己
        创建者不能删除自己
        """
        with self.app.test_request_context():
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            user1 = User.objects(email="1@1.com").first()  # member
            token2 = self.create_user("22", "2@2.com", "222222").generate_token()
            user2 = User.objects(email="2@2.com").first()  # senior
            self.create_user("33", "3@3.com", "333333").generate_token()
            user3 = User.objects(email="3@3.com").first()  # admin
            token4 = self.create_user("44", "4@4.com", "444444").generate_token()
            user4 = User.objects(email="4@4.com").first()  # admin
            token5 = self.create_user("55", "5@5.com", "555555").generate_token()
            user5 = User.objects(email="5@5.com").first()  # 非团队成员
            token6 = self.create_user("66", "6@6.com", "666666").generate_token()
            user6 = User.objects(email="6@6.com").first()  # creator
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("member")
            senior_role = Team.role_cls.by_system_code("senior")
            admin_role = Team.role_cls.by_system_code("admin")
            # 创建team1
            team1 = Team.create(name="t1", creator=user6)
            # 检测有团队
            self.assertEqual(Team.objects.count(), 1)
            # 加入用户
            user1.join(team1, role=member_role)
            user2.join(team1, role=senior_role)
            user3.join(team1, role=admin_role)
            user4.join(team1, role=admin_role)
            self.assertEqual(team1.users().count(), 5)
            # == 资深成员无法删除成员 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user1.id)}",
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 资深成员无法删除管理员 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user3.id)}",
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 管理员无法删除管理员 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user3.id)}",
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 管理员无法删除非团队成员 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user5.id)}",
                token=token4,
            )
            self.assertErrorEqual(data, UserNotExistError)
            # == 非团队成员无法删除成员 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user1.id)}",
                token=token5,
            )
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(team1.users().count(), 5)  # 5个人
            # == 成员可以删除自己 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user1.id)}",
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(team1.users().count(), 4)  # 4个人
            # == 管理员可以删除资深成员 ==
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user2.id)}",
                token=token4,
            )
            self.assertErrorEqual(data)
            self.assertEqual(team1.users().count(), 3)  # 3个人，剩下2个管理员和创建者
            # == 管理员可以删除自己 ==
            self.assertErrorEqual(data)
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user4.id)}",
                token=token4,
            )
            self.assertErrorEqual(data)
            self.assertEqual(team1.users().count(), 2)  # 2个人，管理员和创建者
            # == 创建者不能删除自己 ==
            self.assertErrorEqual(data)
            data = self.delete(
                f"/v1/teams/{str(team1.id)}/users/{str(user6.id)}",
                token=token6,
            )
            self.assertErrorEqual(data, CreatorCanNotLeaveError)
            self.assertEqual(team1.users().count(), 2)  # 2个人，管理员和创建者


class TeamProjectAPITestCase(MoeAPITestCase):
    def test_get_team_project(self):
        """测试获取团队项目"""
        with self.app.test_request_context():
            # == 准备工作 ==
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            user1 = User.by_name("11")
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            team1 = Team.create("t1", creator=user1)
            default_set = team1.default_project_set
            set1 = ProjectSet.create(name="s1", team=team1)
            set2 = ProjectSet.create(name="s2", team=team1)
            # 1 在 default set
            project1 = Project.create("pro1", team=team1, creator=user1)
            # 2 在 set1
            project2 = Project.create("pro2", team=team1, creator=user1)
            project2.move_to_project_set(set1)
            # 3 在 set2
            project3 = Project.create("p3", team=team1, creator=user1)
            project3.move_to_project_set(set2)
            # 4 在 set2
            project4 = Project.create("---", team=team1, creator=user1)
            project4.move_to_project_set(set2)
            # == user2没有权限获取team1的项目 ==
            data = self.get(f"/v1/teams/{str(team1.id)}/projects", token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 获取团队所有项目 ==
            data = self.get(f"/v1/teams/{str(team1.id)}/projects", token=token1)
            self.assertErrorEqual(data)
            self.assertEqual("4", data.headers.get("X-Pagination-Count"))
            # == 根据set筛选 ==
            # default set
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"project_set": str(default_set.id)},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual("pro1", data.json[0]["name"])
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            # set1
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"project_set": str(set1.id)},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual("pro2", data.json[0]["name"])
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            # set2
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"project_set": str(set2.id)},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual("2", data.headers.get("X-Pagination-Count"))
            # == 通过status筛选 ==
            # 初始状态，只有3个进行中的项目
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.WORKING},
                token=token1,
            )
            self.assertEqual("4", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.FINISHED},
                token=token1,
            )
            self.assertEqual("0", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.PLAN_FINISH},
                token=token1,
            )
            self.assertEqual("0", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.PLAN_DELETE},
                token=token1,
            )
            self.assertEqual("0", data.headers.get("X-Pagination-Count"))
            # 将1计划完结，2计划删除，3正式完结，4进行中
            project1.plan_finish()
            project2.plan_delete()
            project3.plan_finish()
            project3.finish()
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.WORKING},
                token=token1,
            )
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.FINISHED},
                token=token1,
            )
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.PLAN_FINISH},
                token=token1,
            )
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.PLAN_DELETE},
                token=token1,
            )
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            # == 通过多个status筛选 ==
            # 其中两个
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={
                    "status": [
                        ProjectStatus.WORKING,
                        ProjectStatus.PLAN_DELETE,
                    ]
                },
                token=token1,
            )
            self.assertEqual("2", data.headers.get("X-Pagination-Count"))
            # 其中三个
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={
                    "status": [
                        ProjectStatus.WORKING,
                        ProjectStatus.PLAN_DELETE,
                        ProjectStatus.PLAN_FINISH,
                    ]
                },
                token=token1,
            )
            self.assertEqual("3", data.headers.get("X-Pagination-Count"))
            # 所有
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"status": ProjectStatus.ids()},
                token=token1,
            )
            self.assertEqual("4", data.headers.get("X-Pagination-Count"))
            # == 通过word筛选 ==
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"word": "pro1"},
                token=token1,
            )
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"word": "pro"},
                token=token1,
            )
            self.assertEqual("2", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"word": "p"},
                token=token1,
            )
            self.assertEqual("3", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"word": "2"},
                token=token1,
            )
            self.assertEqual("1", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"word": "Ro"},
                token=token1,
            )
            self.assertEqual("2", data.headers.get("X-Pagination-Count"))
            data = self.get(
                f"/v1/teams/{str(team1.id)}/projects",
                query_string={"word": "gogogo"},
                token=token1,
            )
            self.assertEqual("0", data.headers.get("X-Pagination-Count"))


class TeamProjectSetAPITestCase(MoeAPITestCase):
    def test_get_team_project_set(self):
        """测试获取团队项目集"""
        with self.app.test_request_context():
            # == 准备工作 ==
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            # 创建一个team
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 初始没有项目集
            self.assertEqual(0, ProjectSet.objects.count())
            # 创建team1
            data1 = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token1,
            )
            self.assertErrorEqual(data1)
            team1 = Team.objects(id=data1.json["team"]["id"]).first()
            # 创建team时自动创建了一个
            self.assertEqual(1, ProjectSet.objects.count())
            # 创建project set
            data = self.post(
                f"/v1/teams/{str(team1.id)}/project-sets",
                json={"name": "p1"},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, ProjectSet.objects.count())
            # == user2没有权限查看 ==
            data = self.get(f"/v1/teams/{str(team1.id)}/project-sets", token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 修改项目集 ==
            data = self.get(f"/v1/teams/{str(team1.id)}/project-sets", token=token1)
            self.assertErrorEqual(data)
            self.assertEqual("default", data.json[0]["name"])
            self.assertEqual("p1", data.json[1]["name"])
            self.assertEqual("2", data.headers.get("X-Pagination-Count"))

    def test_create_team_project_set(self):
        """测试创建团队项目集"""
        with self.app.test_request_context():
            # == 准备工作 ==
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            # 初始没有项目集
            self.assertEqual(0, ProjectSet.objects.count())
            # 创建一个team
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 创建team1
            data1 = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token1,
            )
            self.assertErrorEqual(data1)
            team1 = Team.objects(id=data1.json["team"]["id"]).first()
            # == 测试开始 ==
            self.assertEqual(1, ProjectSet.objects.count())  # team1带有一个默认项目集
            # 创建project set
            data = self.post(
                f"/v1/teams/{str(team1.id)}/project-sets",
                json={"name": "p1"},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, ProjectSet.objects.count())
            # == user2没有权限创建 ==
            data = self.post(
                f"/v1/teams/{str(team1.id)}/project-sets",
                json={"name": "p1"},
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(2, ProjectSet.objects.count())

    def test_edit_team_project_set(self):
        """测试修改团队项目集"""
        with self.app.test_request_context():
            # == 准备工作 ==
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            # 初始没有项目集
            self.assertEqual(0, ProjectSet.objects.count())
            # 创建一个team
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 创建team1
            data1 = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token1,
            )
            self.assertErrorEqual(data1)
            team1 = Team.objects(id=data1.json["team"]["id"]).first()
            # team1自带一个默认项目集
            self.assertEqual(1, ProjectSet.objects.count())
            # 创建project set
            data = self.post(
                f"/v1/teams/{str(team1.id)}/project-sets",
                json={"name": "p1"},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, ProjectSet.objects.count())
            set1 = ProjectSet.objects(default=False).first()
            # == 修改项目集 ==
            self.assertEqual("p1", set1.name)
            data = self.put(
                f"/v1/project-sets/{str(set1.id)}",
                json={"name": "p11"},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, ProjectSet.objects.count())
            set1.reload()
            self.assertEqual("p11", set1.name)
            # == user2没有权限修改 ==
            data = self.put(
                f"/v1/project-sets/{str(set1.id)}",
                json={"name": "p111"},
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(2, ProjectSet.objects.count())
            set1.reload()
            self.assertEqual("p11", set1.name)

    def test_delete_team_project_set(self):
        """测试删除团队项目集"""
        with self.app.test_request_context():
            # == 准备工作 ==
            # 创建用户
            token1 = self.create_user("11", "1@1.com", "111111").generate_token()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            # 初始没有项目集
            self.assertEqual(0, ProjectSet.objects.count())
            # 创建一个team
            # 获取默认角色
            member_role = Team.role_cls.by_system_code("beginner")
            # 创建team1
            data1 = self.post(
                "/v1/teams",
                json={
                    "name": "11",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
                token=token1,
            )
            self.assertErrorEqual(data1)
            team1 = Team.objects(id=data1.json["team"]["id"]).first()
            # team1自带一个默认项目集
            self.assertEqual(1, ProjectSet.objects.count())
            # 创建project set
            data = self.post(
                f"/v1/teams/{str(team1.id)}/project-sets",
                json={"name": "p1"},
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, ProjectSet.objects.count())
            set1 = ProjectSet.objects(name="p1").first()
            # == user2没有权限删除项目集 ==
            data = self.delete(f"/v1/project-sets/{str(set1.id)}", token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(2, ProjectSet.objects.count())
            # == 删除项目集 ==
            data = self.delete(f"/v1/project-sets/{str(set1.id)}", token=token1)
            self.assertErrorEqual(data)
            self.assertEqual(1, ProjectSet.objects.count())
            with self.assertRaises(DoesNotExist):
                set1.reload()

            default_set = team1.default_project_set
            # == user2没有权限删除默认项目集 ==
            data = self.delete(f"/v1/project-sets/{str(default_set.id)}", token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(1, ProjectSet.objects.count())
            # == user也不能删除默认项目集，因为默认项目集不能删除 ==
            data = self.delete(f"/v1/project-sets/{str(default_set.id)}", token=token1)
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(1, ProjectSet.objects.count())
            default_set.reload()

    def test_get_team_insight_user_list1(self):
        """测试获取用户洞悉列表，没有权限"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            data = self.get(f"/v1/teams/{str(team1.id)}/insight/users", token=token1)
            self.assertErrorEqual(data, NoPermissionError)
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            data = self.get(f"/v1/teams/{str(team1.id)}/insight/users", token=token1)
            self.assertErrorEqual(data)

    def test_get_team_insight_user_list2(self):
        """测试获取用户洞悉列表，只会显示团队内的用户和用户的本团队项目"""
        user1 = self.create_user("u1")
        user2 = self.create_user("u2")
        token1 = user1.generate_token()
        team1 = Team.create("t1", creator=user1)
        project1 = Project.create("p1", team=team1, creator=user1)
        project3 = Project.create("p3", team=team1, creator=user1)
        team2 = Team.create("t2", creator=user1)
        project2 = Project.create("p2", team=team2, creator=user1)
        user2.join(team2)
        user2.join(project2)
        data = self.get(f"/v1/teams/{str(team1.id)}/insight/users", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(1, len(data.json))
        self.assertEqual(2, len(data.json[0]["projects"]))
        data = self.get(f"/v1/teams/{str(team2.id)}/insight/users", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(2, len(data.json))
        self.assertEqual(1, len(data.json[0]["projects"]))
        self.assertEqual(1, len(data.json[1]["projects"]))

    def test_get_team_insight_user_list_with_word(self):
        """测试获取用户洞悉列表，通过 word 筛选"""
        user1 = self.create_user("u1")
        user2 = self.create_user("u2")
        token1 = user1.generate_token()
        team1 = Team.create("t2", creator=user1)
        project2 = Project.create("p2", team=team1, creator=user1)
        user2.join(team1)
        user2.join(project2)
        data = self.get(
            f"/v1/teams/{str(team1.id)}/insight/users",
            token=token1,
            query_string={"word": "2"},
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, len(data.json))
        self.assertEqual("u2", data.json[0]["user"]["name"])

    def test_get_team_insight_user_project_list1(self):
        """测试获取用户洞悉项目列表，没有权限"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            user2 = self.create_user("u2")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            user2.join(team1)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/users/{str(user2.id)}/projects",
                token=token1,
            )
            self.assertErrorEqual(data, NoPermissionError)
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/users/{str(user2.id)}/projects",
                token=token1,
            )
            self.assertErrorEqual(data)

    def test_get_team_insight_user_project_list2(self):
        """测试获取用户洞悉项目列表，非本团队成员报不存在"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            user2 = self.create_user("u2")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/users/{str(user2.id)}/projects",
                token=token1,
            )
            self.assertErrorEqual(data, UserNotExistError)
            user2.join(team1)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/users/{str(user2.id)}/projects",
                token=token1,
            )
            self.assertErrorEqual(data)

    def test_get_team_insight_user_project_list3(self):
        """测试获取用户洞悉项目列表"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            user2 = self.create_user("u2")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            user2.join(team1)
            project1 = Project.create("p1", team=team1)
            user2.join(project1)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/users/{str(user2.id)}/projects",
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))

    def test_get_team_insight_project_list1(self):
        """测试获取项目洞悉列表，没有权限"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects",
                token=token1,
            )
            self.assertErrorEqual(data, NoPermissionError)
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects",
                token=token1,
            )
            self.assertErrorEqual(data)

    def test_get_team_insight_project_list2(self):
        """测试获取项目洞悉列表，只会显示团队内的项目"""
        user1 = self.create_user("u1")
        token1 = user1.generate_token()
        team1 = Team.create("t1", creator=user1)
        team2 = Team.create("t2", creator=user1)
        Project.create("p1", team=team1)
        Project.create("p2", team=team2)
        data = self.get(
            f"/v1/teams/{str(team1.id)}/insight/projects",
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, len(data.json))
        self.assertEqual("p1", data.json[0]["project"]["name"])

    def test_get_team_insight_project_list_with_word(self):
        """测试获取项目洞悉列表，通过 word 筛选"""
        user1 = self.create_user("u1")
        token1 = user1.generate_token()
        team1 = Team.create("t1", creator=user1)
        Project.create("p1", team=team1)
        Project.create("p2", team=team1)
        data = self.get(
            f"/v1/teams/{str(team1.id)}/insight/projects",
            token=token1,
            query_string={"word": "2"},
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, len(data.json))
        self.assertEqual("p2", data.json[0]["project"]["name"])

    def test_get_team_insight_project_user_list1(self):
        """测试获取项目洞悉项目列表，没有权限"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            project1 = Project.create("p1", team=team1)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects/{str(project1.id)}/users",
                token=token1,
            )
            self.assertErrorEqual(data, NoPermissionError)
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects/{str(project1.id)}/users",
                token=token1,
            )
            self.assertErrorEqual(data)

    def test_get_team_insight_project_user_list2(self):
        """测试获取项目洞悉项目列表，非本团队项目报不存在"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            team2 = Team.create("t2")
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            project1 = Project.create("p1", team=team1)
            project2 = Project.create("p1", team=team2)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects/{str(project1.id)}/users",
                token=token1,
            )
            self.assertErrorEqual(data)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects/{str(project2.id)}/users",
                token=token1,
            )
            self.assertErrorEqual(data, ProjectNotExistError)

    def test_get_team_insight_project_user_list3(self):
        """测试获取用户洞悉项目列表"""
        with self.app.test_request_context():
            user1 = self.create_user("u1")
            token1 = user1.generate_token()
            team1 = Team.create("t1")
            admin_role = Team.role_cls.by_system_code("admin")
            user1.join(team1, role=admin_role)
            project1 = Project.create("p1", team=team1)
            user1.join(project1)
            data = self.get(
                f"/v1/teams/{str(team1.id)}/insight/projects/{str(project1.id)}/users",
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))

    def test_only_allow_admin_create_team(self):
        """测试只有管理员才能创建团队"""
        with self.app.test_request_context():
            member_role = Team.role_cls.by_system_code("beginner")
            site_setting = SiteSetting.get()
            site_setting.only_allow_admin_create_team = True
            site_setting.save()
            site_setting.reload()
            self.assertTrue(site_setting.only_allow_admin_create_team)
            # 普通用户创建团队失败
            user1 = self.create_user("u1")
            user_token1 = user1.generate_token()
            data = self.post(
                "/v1/teams",
                token=user_token1,
                json={
                    "name": "t1",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
            )
            self.assertErrorEqual(data, OnlyAllowAdminCreateTeamError)
            self.assertEqual(Team.objects(name="t1").count(), 0)
            # 管理员创建团队成功
            admin1 = self.create_user("admin1")
            admin1.admin = True
            admin1.save()
            admin_token1 = admin1.generate_token()
            data = self.post(
                "/v1/teams",
                token=admin_token1,
                json={
                    "name": "at1",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
            )
            self.assertErrorEqual(data)
            self.assertEqual(Team.objects(name="at1").count(), 1)
            # 关闭仅管理员创建团队，普通用户创建团队成功
            site_setting.only_allow_admin_create_team = False
            site_setting.save()
            site_setting.reload()
            self.assertFalse(site_setting.only_allow_admin_create_team)
            data = self.post(
                "/v1/teams",
                token=user_token1,
                json={
                    "name": "t2",
                    "allow_apply_type": AllowApplyType.NONE,
                    "application_check_type": ApplicationCheckType.ADMIN_CHECK,
                    "default_role": str(member_role.id),
                    "intro": "",
                },
            )
            self.assertErrorEqual(data)
            self.assertEqual(Team.objects(name="t2").count(), 1)
