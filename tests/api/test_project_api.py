from app.constants.project import ProjectStatus
from app.constants.source import SourcePositionType
from app.exceptions import (
    CreatorCanNotLeaveError,
    NeedTokenError,
    NoPermissionError,
    ProjectFinishedError,
    ProjectHasDeletePlanError,
    ProjectHasFinishPlanError,
    ProjectNoDeletePlanError,
    ProjectNoFinishPlanError,
    ProjectNotFinishedError,
    ProjectSetNotExistError,
    RequestDataEmptyError,
    RoleNotExistError,
    UserNotExistError,
)
from app.constants.file import FileNotExistReason
from app.exceptions.language import SameTargetLanguageError
from app.models.language import Language
from app.models.project import Project, ProjectRole, ProjectSet
from app.models.team import Team
from app.models.user import User
from flask_apikit.exceptions import ValidateError
from tests import MoeAPITestCase


class ProjectAPITestCase(MoeAPITestCase):
    def test_get_project(self):
        """测试获取项目"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        User.by_name("22")
        team1 = Team.create(name="t1", creator=user1)
        project1 = Project.create(name="p1", team=team1)
        # 未登录，没有权限访问
        data = self.get(f"/v1/projects/{str(project1.id)}")
        self.assertErrorEqual(data, NeedTokenError)
        # user2没有权限访问
        data = self.get(f"/v1/projects/{str(project1.id)}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # user1可以访问
        data = self.get(f"/v1/projects/{str(project1.id)}", token=token1)
        self.assertEqual(str(project1.id), data.json["id"])
        self.assertEqual(str(project1.name), data.json["name"])

    def test_auto_become_project_admin(self):
        """
        测试获取项目，自动成为管理员返回值是否正确
        1. 测试单个项目接口返回值
        2. 测试团队项目列表接口返回值
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        team1 = Team.create(name="t1", creator=user1)
        project1 = Project.create(name="p1", team=team1)
        project2 = Project.create(name="p2", team=team1)
        project3 = Project.create(name="p3", team=team1)
        user1.join(project1, role=ProjectRole.by_system_code("admin"))
        user1.join(project2, role=ProjectRole.by_system_code("translator"))
        # ======= 1. 测试单个项目接口返回值 =======
        # project1 是管理员，但是是自己加入的
        data = self.get(f"/v1/projects/{str(project1.id)}", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual("admin", data.json["role"]["system_code"])
        self.assertEqual(False, data.json["auto_become_project_admin"])
        # project2 是翻译，是自己加入的
        data = self.get(f"/v1/projects/{str(project2.id)}", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual("translator", data.json["role"]["system_code"])
        self.assertEqual(False, data.json["auto_become_project_admin"])
        # project3 是管理员，是继承自团队
        data = self.get(f"/v1/projects/{str(project3.id)}", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual("admin", data.json["role"]["system_code"])
        self.assertEqual(True, data.json["auto_become_project_admin"])
        # ======= 2. 测试团队项目列表接口返回值 =======
        data = self.get(f"/v1/teams/{str(team1.id)}/projects", token=token1)
        self.assertErrorEqual(data)
        projects_data = {d["id"]: d for d in data.json}
        # project1 是管理员，但是是自己加入的
        self.assertEqual(
            "admin", projects_data[str(project1.id)]["role"]["system_code"]
        )
        self.assertEqual(
            False, projects_data[str(project1.id)]["auto_become_project_admin"]
        )
        # project2 是翻译，是自己加入的
        self.assertEqual(
            "translator", projects_data[str(project2.id)]["role"]["system_code"]
        )
        self.assertEqual(
            False, projects_data[str(project2.id)]["auto_become_project_admin"]
        )
        # project3 是管理员，是继承自团队
        self.assertEqual(
            "admin", projects_data[str(project3.id)]["role"]["system_code"]
        )
        self.assertEqual(
            True, projects_data[str(project3.id)]["auto_become_project_admin"]
        )

    def test_create_project(self):
        """测试创建项目"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        team2 = Team.create(name="t2", creator=user1)
        set1 = team1.default_project_set
        set2 = team2.default_project_set
        # 未登录，没有权限创建
        data = self.post(f"/v1/teams/{str(team1.id)}/projects")
        self.assertErrorEqual(data, NeedTokenError)
        # user2没有权限创建
        data = self.post(f"/v1/teams/{str(team1.id)}/projects", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 没有参数不能创建
        data = self.post(f"/v1/teams/{str(team1.id)}/projects", token=token1)
        self.assertErrorEqual(data, ValidateError)
        # 缺少参数不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={"name": "p1"},
        )
        self.assertErrorEqual(data, ValidateError)
        # 源语言缺少不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 源语言不存在不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "400440044004400440044004",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 目标语言缺少不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 目标语言为空数组不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": [],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 目标语言为中都不存在不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": [
                    "400440044004400440044004",
                    "500440044004400440044004",
                ],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 目标语言为中某一个不存在不能创建
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": [
                    "zh-CN",
                    "404404404404404404404404",
                ],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # allow_apply_type不能设置为错误的值
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "",
                "project_set": str(set1.id),
                "allow_apply_type": 999,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("creator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 不能设置默认角色为创建者
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("creator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 不能设置默认角色为team的角色
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Team.role_cls.by_system_code("beginner").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data, ValidateError)
        # 其他team的项目集 报错
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set2.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data, ProjectSetNotExistError)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )

    def test_edit_project(self):
        """测试修改项目"""
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        set1 = team1.default_project_set
        set2 = ProjectSet.create("s2", team=team1)
        team2 = Team.create(name="t2", creator=user1)
        set3 = ProjectSet.create("s3", team=team2)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(set1, project1.project_set)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # 没有登录不能修改
        data = self.put(f"/v1/projects/{str(project1.id)}")
        self.assertErrorEqual(data, NeedTokenError)
        # 没有权限不能修改
        data = self.put(f"/v1/projects/{str(project1.id)}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 没有参数不能修改
        data = self.put(f"/v1/projects/{str(project1.id)}", token=token1)
        self.assertErrorEqual(data, RequestDataEmptyError)
        # 创建一个自定义角色
        role1 = project1.create_role(
            name="test_role1", level=3, permissions=[], operator=user1
        )
        # 角色不能设置成创建者
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={"default_role": str(Project.role_cls.by_system_code("creator").id)},
        )
        self.assertErrorEqual(data, ValidateError)
        # 角色不能设置成team的角色
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={"default_role": str(Team.role_cls.by_system_code("beginner").id)},
        )
        self.assertErrorEqual(data, ValidateError)
        # allow_apply_type不能设置为错误的值
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={"allow_apply_type": 999},
        )
        self.assertErrorEqual(data, ValidateError)
        # 角色可以设置成自定义角色
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={"default_role": str(role1.id)},
        )
        self.assertErrorEqual(data)
        # 修改其他
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={
                "name": "pp1",
                "intro": "ppi1",
                "allow_apply_type": Project.allow_apply_type_cls.NONE,
            },
        )
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual("pp1", project1.name)
        self.assertEqual("ppi1", project1.intro)
        self.assertEqual(Project.allow_apply_type_cls.NONE, project1.allow_apply_type)
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(role1, project1.default_role)
        # 修改项目集
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={"project_set": str(set2.id)},
        )
        project1.reload()
        self.assertErrorEqual(data)
        self.assertEqual(set2, project1.project_set)
        # 修改成team2的项目集报错
        data = self.put(
            f"/v1/projects/{str(project1.id)}",
            token=token1,
            json={"project_set": str(set3.id)},
        )
        project1.reload()
        self.assertErrorEqual(data, ProjectSetNotExistError)
        self.assertEqual(set2, project1.project_set)

    def test_plan_finish_project1(self):
        """
        测试完结项目:
        - 未登录不能计划完结
        - 没有权限不能计划完结
        - 正常计划完结
        - 已经有完结计划的不能再次计划完结
        - 已经正式完结的不能计划完结
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects(name="p1").first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # 未登录不能计划完结
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        data = self.post(
            f"/v1/projects/{str(project1.id)}/finish-plan",
        )
        self.assertErrorEqual(data, NeedTokenError)
        # 没有权限不能计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 正常计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 已有完结计划的，不能再次计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data, ProjectHasFinishPlanError)
        # 将项目正式完结
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 已经正式完结的，不能计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data, ProjectFinishedError)

    def test_plan_finish_project2(self):
        """
        测试完结项目:
        - 有销毁计划的不能计划完结
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # 计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # ===== 开始测试 =====
        # 已经计划销毁的，不能计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data, ProjectHasDeletePlanError)

    def test_finish1(self):
        """
        - 不在PLAN_FINISH中的项目不能完结
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # 计划销毁
        project1.plan_delete()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        # PLAN_DELETE 状态的项目不能完结
        with self.assertRaises(ProjectNoFinishPlanError):
            project1.finish()
        project1.reload()  # finish()抛出错误时候不会reload，强制reload一下
        # 取消销毁计划
        project1.cancel_delete_plan()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        # 计划完结
        project1.plan_finish()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        # PLAN_FINISH 状态的项目可以完结
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        # FINISHED 状态的项目不能完结
        with self.assertRaises(ProjectNoFinishPlanError):
            project1.finish()
        project1.reload()  # finish()抛出错误时候不会reload，强制reload一下
        self.assertEqual(ProjectStatus.FINISHED, project1.status)

    def test_plan_delete_project1(self):
        """
        测试计划销毁项目：
        - 未登录不能计划销毁
        - 没有权限不能计划销毁
        - 正常计划销毁
        - 已有销毁计划的，不能再次计划销毁
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # 未登录不能计划销毁
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan")
        self.assertErrorEqual(data, NeedTokenError)
        # 没有权限不能计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 正常计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # 已有销毁计划的，不能再次计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data, ProjectHasDeletePlanError)

    def test_plan_delete_project2(self):
        """
        测试计划销毁项目：
        - 已有完结计划的，不能计划销毁
        - 已经正式完结的，项目还是可以计划销毁
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # 将项目计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # ===== 开始测试 =====
        # 已经计划完结的，不能销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data, ProjectHasFinishPlanError)
        # 将项目正式完结
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 已经正式完结的，项目还是可以计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)

    def test_cancel_finish_plan1(self):
        """
        测试取消计划完结项目：
        - 未登录不能取消完结计划
        - 没有权限不能取消完结计划
        - 正常取消完结计划（恢复成WORKING状态）
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # 将项目计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # ===== 开始测试 =====
        # 未登录不能取消完结计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan")
        self.assertErrorEqual(data, NeedTokenError)
        # 没有权限不能取消完结计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 正常取消完结计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)

    def test_cancel_finish_plan2(self):
        """
        测试取消项目完结计划：
        - WORKING中的项目不能取消
        - PLAN_DELETE中的项目不能取消
        - FINISHED中的项目不能取消
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # WORKING的项目不能取消
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data, ProjectNoFinishPlanError)
        project1.reload()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 将项目计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # PLAN_DELETE的项目不能取消
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data, ProjectNoFinishPlanError)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # 取消销毁计划，并完结
        project1.cancel_delete_plan()
        project1.plan_finish()
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # FINISHED的项目不能取消
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data, ProjectNoFinishPlanError)
        project1.reload()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)

    def test_cancel_delete_plan1(self):
        """
        测试取消项目销毁计划：
        - 未登录不能取消销毁计划
        - 没有权限不能取消销毁计划
        - 正常取消销毁计划（恢复成WORKING状态）
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # 将项目计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # ===== 开始测试 =====
        # 未登录不能取消销毁计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan")
        self.assertErrorEqual(data, NeedTokenError)
        # 没有权限不能取消销毁计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 正常取消销毁计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)

    def test_cancel_delete_plan2(self):
        """
        测试取消项目销毁计划：
        - WORKING中的项目不能取消
        - PLAN_FINISH中的项目不能取消
        - FINISHED中的项目不能取消
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # WORKING的项目不能取消
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data, ProjectNoDeletePlanError)
        project1.reload()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 将项目计划完结
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # PLAN_FINISH的项目不能取消
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data, ProjectNoDeletePlanError)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 将项目完结
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # FINISHED的项目不能取消
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data, ProjectNoDeletePlanError)
        project1.reload()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)

    def test_cancel_delete_plan3(self):
        """
        测试取消项目销毁计划：
        - 已经正式完结的，计划销毁后，取消销毁计划（恢复成FINISHED状态）
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # 完结项目
        project1.plan_finish()
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # 取消销毁计划后，恢复到FINISHED状态
        data = self.delete(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)

    def test_resume1(self):
        """
        测试取消计划销毁项目：
        - 未登录不能恢复项目
        - 没有权限不能恢复项目
        - 正常恢复项目
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # 将项目完结
        project1.plan_finish()
        project1.finish()
        self.assertEqual(ProjectStatus.FINISHED, project1.status)
        self.assertIsNotNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # ===== 开始测试 =====
        # 未登录不能恢复项目
        data = self.post(
            f"/v1/projects/{str(project1.id)}/resume",
        )
        self.assertErrorEqual(data, NeedTokenError)
        # 没有权限不能恢复项目
        data = self.post(f"/v1/projects/{str(project1.id)}/resume", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 正常恢复项目
        data = self.post(f"/v1/projects/{str(project1.id)}/resume", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)

    def test_resume2(self):
        """
        测试取消计划销毁项目：
        - WORKING状态的项目不能resume
        - PLAN_FINISH状态的项目不能resume
        - PLAN_DELETE状态的项目不能resume
        """
        # ===== 准备工作 =====
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project_set_id = str(team1.default_project_set.id)
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": project_set_id,
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Project.objects.count())
        project1 = Project.objects.first()
        self.assertEqual(data.json["project"]["id"], str(project1.id))
        self.assertEqual("p1", project1.name)
        self.assertEqual("pi1", project1.intro)
        self.assertEqual(
            Project.allow_apply_type_cls.TEAM_USER, project1.allow_apply_type
        )
        self.assertEqual(
            Project.application_check_type_cls.ADMIN_CHECK,
            project1.application_check_type,
        )
        self.assertEqual(
            Project.role_cls.by_system_code("translator"),
            project1.default_role,
        )
        # ===== 开始测试 =====
        # WORKING状态的项目不能resume
        data = self.post(f"/v1/projects/{str(project1.id)}/resume", token=token1)
        self.assertErrorEqual(data, ProjectNotFinishedError)
        # 计划完成
        data = self.post(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_FINISH, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNotNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # PLAN_FINISH状态的项目不能resume
        data = self.post(f"/v1/projects/{str(project1.id)}/resume", token=token1)
        self.assertErrorEqual(data, ProjectNotFinishedError)
        # 取消计划
        data = self.delete(f"/v1/projects/{str(project1.id)}/finish-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.WORKING, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNone(project1.plan_delete_time)
        # 计划销毁
        data = self.post(f"/v1/projects/{str(project1.id)}/delete-plan", token=token1)
        self.assertErrorEqual(data)
        project1.reload()
        self.assertEqual(ProjectStatus.PLAN_DELETE, project1.status)
        self.assertIsNone(project1.system_finish_time)
        self.assertIsNone(project1.plan_finish_time)
        self.assertIsNotNone(project1.plan_delete_time)
        # PLAN_DELETE状态的项目不能resume
        data = self.post(f"/v1/projects/{str(project1.id)}/resume", token=token1)
        self.assertErrorEqual(data, ProjectNotFinishedError)

    def test_get_project_users(self):
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
            user2 = User.objects(email="2@2.com").first()  # proofreader
            token3 = self.create_user("33", "3@3.com", "333333").generate_token()
            User.objects(email="3@3.com").first()  # 非团队成员
            # 创建project1
            team1 = Team.create(name="t1")
            project1 = Project.create(name="p1", team=team1, creator=user1)
            proofreader_role = Project.role_cls.by_system_code("proofreader")
            user2.join(project1, role=proofreader_role)
            # == 非团队成员无法访问 ==
            data = self.get(f"/v1/projects/{str(project1.id)}/users", token=token3)
            self.assertErrorEqual(data, NoPermissionError)
            # == 使用 word 限制搜索 ==
            # == 返回的 role 是否正确 ==
            # 获取 2 个
            data = self.get(f"/v1/projects/{str(project1.id)}/users", token=token1)
            self.assertErrorEqual(data)
            self.assertEqual(2, len(data.json))
            # 单独获取用户 11
            data = self.get(
                f"/v1/projects/{str(project1.id)}/users?word=1", token=token2
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual("creator", data.json[0]["role"]["system_code"])
            # 单独获取用户 22
            data = self.get(
                f"/v1/projects/{str(project1.id)}/users?word=2", token=token2
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, len(data.json))
            self.assertEqual("proofreader", data.json[0]["role"]["system_code"])

    def test_edit_project_user(self):
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
            # 创建project1
            team1 = Team.create(name="t1", creator=user1)
            project1 = Project.create(name="p1", team=team1, creator=user5)
            project2 = Project.create(name="t2", team=team1)
            supporter_role = Project.role_cls.by_system_code("supporter")
            translator_role = Project.role_cls.by_system_code("translator")
            proofreader_role = Project.role_cls.by_system_code("proofreader")
            admin_role = Project.role_cls.by_system_code("admin")
            creator_role = Project.role_cls.by_system_code("creator")
            user1.join(project1, role=supporter_role)
            user2.join(project1, role=translator_role)
            user3.join(project1, role=proofreader_role)
            user4.join(project1, role=admin_role)
            user4_2.join(project1, role=admin_role)
            # 创建自定义角色
            role1 = project1.create_role("t1r", 0, permissions=[1])
            role2 = project2.create_role("t2r", 0, permissions=[1])
            # == “非团队成员”不能修改角色 ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user1.id)}",
                json={"role": str(translator_role.id)},
                token=token6,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改“非团队成员”角色 ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user6.id)}",
                json={"role": str(translator_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, UserNotExistError)
            # == “资深成员”不能修改“见习成员”角色（没有权限） ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user1.id)}",
                json={"role": str(translator_role.id)},
                token=token3,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改“管理员”角色（等级一样） ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user4_2.id)}",
                json={"role": str(translator_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改“创建者”角色（等级低） ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user5.id)}",
                json={"role": str(translator_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改成员为“管理员”角色（等级一样） ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                json={"role": str(admin_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”不能修改成员为“创建者”角色（等级低） ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                json={"role": str(creator_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == “管理员”可以修改“成员”为“见习成员”角色 ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                json={"role": str(supporter_role.id)},
                token=token4,
            )
            self.assertErrorEqual(data)
            user2.reload()
            self.assertEqual(supporter_role, user2.get_role(project1))
            # == 可以使用自定义角色 ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                json={"role": str(role1.id)},
                token=token4,
            )
            self.assertErrorEqual(data)
            user2.reload()
            self.assertEqual(role1, user2.get_role(project1))
            # == 不能使用其他团队的自定义角色 ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                json={"role": str(role2.id)},
                token=token4,
            )
            self.assertErrorEqual(data, RoleNotExistError)
            user2.reload()
            self.assertEqual(role1, user2.get_role(project1))  # 仍然是 role1
            # == 不能使用不存在的自定义角色 ==
            data = self.put(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                json={"role": "5e86e6303fb2000000000000"},
                token=token4,
            )
            self.assertErrorEqual(data, RoleNotExistError)
            user2.reload()
            self.assertEqual(role1, user2.get_role(project1))  # 仍然是 role1

    def test_delete_project_user(self):
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
            user1 = User.objects(email="1@1.com").first()  # translator
            token2 = self.create_user("22", "2@2.com", "222222").generate_token()
            user2 = User.objects(email="2@2.com").first()  # proofreader
            self.create_user("33", "3@3.com", "333333").generate_token()
            user3 = User.objects(email="3@3.com").first()  # admin
            token4 = self.create_user("44", "4@4.com", "444444").generate_token()
            user4 = User.objects(email="4@4.com").first()  # admin
            token5 = self.create_user("55", "5@5.com", "555555").generate_token()
            user5 = User.objects(email="5@5.com").first()  # 非团队成员
            token6 = self.create_user("66", "6@6.com", "666666").generate_token()
            user6 = User.objects(email="6@6.com").first()  # creator
            # 获取默认角色
            translator_role = Project.role_cls.by_system_code("translator")
            proofreader_role = Project.role_cls.by_system_code("proofreader")
            admin_role = Project.role_cls.by_system_code("admin")
            # 创建project1
            team1 = Team.create(name="t1", creator=user1)
            project1 = Project.create(name="p1", team=team1, creator=user6)
            # 检测有团队
            self.assertEqual(Project.objects.count(), 1)
            # 加入用户
            user1.join(project1, role=translator_role)
            user2.join(project1, role=proofreader_role)
            user3.join(project1, role=admin_role)
            user4.join(project1, role=admin_role)
            self.assertEqual(project1.users().count(), 5)
            # == 资深成员无法删除成员 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user1.id)}",
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 资深成员无法删除管理员 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user3.id)}",
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 管理员无法删除管理员 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user3.id)}",
                token=token4,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 管理员无法删除非团队成员 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user5.id)}",
                token=token4,
            )
            self.assertErrorEqual(data, UserNotExistError)
            # == 非团队成员无法删除成员 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user1.id)}",
                token=token5,
            )
            self.assertErrorEqual(data, NoPermissionError)
            self.assertEqual(project1.users().count(), 5)  # 5个人
            # == 成员可以删除自己 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user1.id)}",
                token=token1,
            )
            self.assertErrorEqual(data)
            self.assertEqual(project1.users().count(), 4)  # 4个人
            # == 管理员可以删除资深成员 ==
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user2.id)}",
                token=token4,
            )
            self.assertErrorEqual(data)
            self.assertEqual(project1.users().count(), 3)  # 3个人，剩下2个管理员和创建者
            # == 管理员可以删除自己 ==
            self.assertErrorEqual(data)
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user4.id)}",
                token=token4,
            )
            self.assertErrorEqual(data)
            self.assertEqual(project1.users().count(), 2)  # 2个人，管理员和创建者
            # == 创建者不能删除自己 ==
            self.assertErrorEqual(data)
            data = self.delete(
                f"/v1/projects/{str(project1.id)}/users/{str(user6.id)}",
                token=token6,
            )
            self.assertErrorEqual(data, CreatorCanNotLeaveError)
            self.assertEqual(project1.users().count(), 2)  # 2个人，管理员和创建者

    def test_get_targets(self):
        """测试获取翻译目标"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        team1 = Team.create(name="t1", creator=user1)
        project1 = Project.create(name="p1", team=team1)
        # 未登录，没有权限访问
        data = self.get(f"/v1/projects/{str(project1.id)}")
        self.assertErrorEqual(data, NeedTokenError)
        # user2没有权限访问
        data = self.get(f"/v1/projects/{str(project1.id)}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # user1可以访问
        data = self.get(f"/v1/projects/{str(project1.id)}", token=token1)
        self.assertEqual(str(project1.id), data.json["id"])
        self.assertEqual(str(project1.name), data.json["name"])

    def test_create_target(self):
        """测试获取翻译目标"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        token1 = self.get_creator(project).generate_token()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        # 未登录，没有权限访问
        data = self.post(f"/v1/projects/{str(project.id)}/targets")
        self.assertErrorEqual(data, NeedTokenError)
        self.assertEqual(project.targets().count(), 1)
        # user2，没有权限访问
        data = self.post(f"/v1/projects/{str(project.id)}/targets", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        self.assertEqual(project.targets().count(), 1)
        # user1，缺少语言
        data = self.post(f"/v1/projects/{str(project.id)}/targets", token=token1)
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(project.targets().count(), 1)
        # user1，语言重复
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets",
            token=token1,
            json={"language": "en"},
        )
        self.assertErrorEqual(data, SameTargetLanguageError)
        self.assertEqual(project.targets().count(), 1)
        # user1，正常访问
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets",
            token=token1,
            json={"language": "ko"},
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.targets().count(), 2)
        self.assertListEqual(
            sorted([t.language.code for t in project.targets()]), sorted(["ko", "en"])
        )

    def test_delete_target(self):
        """测试获取翻译目标"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        token1 = self.get_creator(project).generate_token()
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        target = project.targets().first()
        # 未登录，没有权限访问
        data = self.delete(f"/v1/targets/{str(target.id)}")
        self.assertErrorEqual(data, NeedTokenError)
        self.assertEqual(project.targets().count(), 1)
        # user2，没有权限访问
        data = self.delete(f"/v1/targets/{str(target.id)}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        self.assertEqual(project.targets().count(), 1)
        # user1，正常访问
        data = self.delete(f"/v1/targets/{str(target.id)}", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(project.targets().count(), 0)

    def test_edit_finished_project(self):
        """测试修改已完结的项目"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        token = self.get_creator(project).generate_token()
        project.finish()
        data = self.put(
            f"/v1/projects/{str(project.id)}", json={"name": "123"}, token=token
        )
        self.assertErrorEqual(data, ProjectFinishedError)

    def test_finish_finished_project(self):
        """测试完结已完结的项目"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        token = self.get_creator(project).generate_token()
        project.finish()
        data = self.delete(f"/v1/projects/{str(project.id)}", token=token)
        self.assertErrorEqual(data, ProjectFinishedError)

    def test_create_project_with_labelplus_txt1(self):
        """测试创建项目使用空 labelplus_txt"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        team1 = Team.create(name="t1", creator=user1)
        set1 = team1.default_project_set
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
                "labelplus_txt": "",
            },
        )
        self.assertErrorEqual(data)

    def test_create_project_with_labelplus_txt2(self):
        """测试创建项目使用空 labelplus_txt"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        team1 = Team.create(name="t1", creator=user1)
        set1 = team1.default_project_set
        # 正常创建
        self.assertEqual(0, Project.objects.count())
        data = self.post(
            f"/v1/teams/{str(team1.id)}/projects",
            token=token1,
            json={
                "name": "p1",
                "intro": "pi1",
                "project_set": str(set1.id),
                "allow_apply_type": Project.allow_apply_type_cls.TEAM_USER,
                "application_check_type": Project.application_check_type_cls.ADMIN_CHECK,  # noqa: E501
                "default_role": str(Project.role_cls.by_system_code("translator").id),
                "source_language": "ja",
                "target_languages": ["zh-CN"],
                "labelplus_txt": """1,0
-
框内
框外
-
由MoeTra.com导出
>>>>>>>>[1.jpg]<<<<<<<<
----------------[1]----------------[0.509,0.270,1]
第一行

第三行
----------------[2]----------------[0.725,0.271,2]
第一行


>>>>>>>>[2.jpeg]<<<<<<<<""",
            },
        )
        self.assertErrorEqual(data)
        project = Project.objects.first()
        target = project.targets().first()
        files = project.files()
        # 校验文件
        self.assertEqual(files.count(), 2)
        self.assertEqual(files[0].name, "1.jpg")
        self.assertEqual(files[0].file_size, 0)
        self.assertEqual(files[0].file_not_exist_reason, FileNotExistReason.NOT_UPLOAD)
        self.assertEqual(files[1].name, "2.jpeg")
        # 校验原文
        sources = files[0].sources()
        self.assertEqual(sources.count(), 2)
        self.assertEqual(sources[0].position_type, SourcePositionType.IN)
        self.assertEqual(sources[1].position_type, SourcePositionType.OUT)
        # 校验翻译
        source0_translations = sources[0].translations()
        self.assertEqual(source0_translations.count(), 1)
        self.assertEqual(source0_translations[0].content, "第一行\n\n第三行")
        self.assertEqual(source0_translations[0].user, user1)
        self.assertEqual(source0_translations[0].target, target)
        source1_translations = sources[1].translations()
        self.assertEqual(source1_translations.count(), 1)
        self.assertEqual(source1_translations[0].content, "第一行\n\n")
