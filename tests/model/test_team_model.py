import os

from flask import current_app

from app import oss
from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.exceptions import (
    AllowApplyTypeNotExistError,
    ApplicationCheckTypeNotExistError,
    PermissionNotExistError,
    RoleNotExistError,
)
from app.models.application import Application
from app.models.file import File, Source, Tip, Translation
from app.models.invitation import Invitation
from app.models.language import Language
from app.models.project import (
    Project,
    ProjectRole,
    ProjectSet,
    ProjectUserRelation,
)
from app.models.team import Team, TeamPermission, TeamRole, TeamUserRelation
from app.models.term import Term, TermBank
from app.models.user import User
from app.constants.project import ProjectStatus
from tests import (
    DEFAULT_PROJECT_SETS_COUNT,
    DEFAULT_TEAM_USER_RELATIONS,
    DEFAULT_TEAMS_COUNT,
    TEST_FILE_PATH,
    MoeTestCase,
)


class TeamModelTestCase(MoeTestCase):
    def test_create_with_default_kwargs(self):
        """测试默认的创建属性"""
        team = Team.create("t1")
        self.assertEqual("t1", team.name)
        self.assertEqual(TeamRole.by_system_code("beginner"), team.default_role)
        self.assertEqual("", team.intro)
        self.assertEqual(AllowApplyType.NONE, team.allow_apply_type)
        self.assertEqual(ApplicationCheckType.ADMIN_CHECK, team.application_check_type)

    def test_join_leave_team(self):
        """测试加入/离开团队"""
        team = Team.create("t1")
        user1 = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        # 加入了一位
        user1.join(team, role=TeamRole.by_system_code("creator"))
        users = team.users()
        self.assertIsNotNone(user1.get_relation(team))
        self.assertIsNone(user2.get_relation(team))
        self.assertTrue(user1 in users)
        self.assertFalse(user2 in users)
        self.assertEqual(users.count(), 1)
        # 加入了两位
        user2.join(team, role=TeamRole.by_system_code("admin"))
        users = team.users()
        self.assertTrue(user1 in users)
        self.assertTrue(user2 in users)
        self.assertEqual(users.count(), 2)
        # 离开了一位
        user2.leave(team)
        users = team.users()
        self.assertTrue(user1 in users)
        self.assertFalse(user2 in users)
        self.assertEqual(users.count(), 1)

    def test_change_role(self):
        """测试改变团队角色"""
        team = Team.create("t1")
        user = User(name="u1", email="u1").save()
        role1 = TeamRole.objects.first()
        role2 = TeamRole.objects.skip(1).first()
        user.join(team, role=role1)
        self.assertIsNotNone(user.get_relation(team))
        self.assertEqual(user.get_role(team), role1)
        user.set_role(team, role2)
        self.assertEqual(user.get_role(team), role2)

    def test_get_users(self):
        """测试获取团队用户"""
        team = Team.create("t1")
        user1 = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        user3 = User(name="u3", email="u3").save()
        role1 = TeamRole.objects(system_code="beginner").first()
        role2 = TeamRole.objects(system_code="admin").first()
        user1.join(team, role1)
        user2.join(team, role1)
        user3.join(team, role2)
        self.assertEqual(len(team.users(skip=1, limit=1)), 1)
        self.assertEqual(team.users(skip=1, limit=1).first().name, "u2")
        self.assertEqual(team.users().count(), 3)
        self.assertEqual(len(team.users(role1)), 2)
        self.assertEqual(len(team.users(role2)), 1)
        self.assertEqual(len(team.users([role1, role2])), 3)

    def test_get_projects(self):
        """测试获取团队的项目"""
        team = Team.create("t1")
        project_set = ProjectSet.create(name="ps1", team=team)
        default_project_set = team.default_project_set
        project1 = Project.create(name="p1", team=team)
        project2 = Project.create(name="p2", team=team)
        project3 = Project.create(name="p3", team=team)
        self.assertEqual(1, len(team.projects(skip=1, limit=1)))  # 测试分页是否起效
        self.assertEqual("p2", team.projects(skip=1, limit=1).first().name)
        self.assertEqual(3, team.projects().count())
        self.assertEqual(
            3, team.projects(skip=1, limit=1).count()
        )  # skip,limit不影响count
        # 将1个项目加入set，1个项目完成，检查projects()的变量是否生效
        self.assertEqual(3, team.projects(status=None).count())
        self.assertEqual(3, team.projects(status=ProjectStatus.WORKING).count())
        self.assertEqual(0, team.projects(status=ProjectStatus.FINISHED).count())
        self.assertEqual(3, team.projects(status=ProjectStatus.WORKING).count())
        self.assertEqual(0, team.projects(status=ProjectStatus.FINISHED).count())
        self.assertEqual(3, team.projects(status=None).count())
        # project1完成，现在在默认项目集有2个进行中，1个完成
        project1.status = ProjectStatus.FINISHED
        project1.save()
        project1.reload()
        # 测试数量
        # 全部
        self.assertEqual(3, team.projects(status=None).count())
        self.assertEqual(2, team.projects(status=ProjectStatus.WORKING).count())
        self.assertEqual(1, team.projects(status=ProjectStatus.FINISHED).count())
        # 默认项目集
        self.assertEqual(
            3,
            team.projects(project_set=default_project_set, status=None).count(),
        )
        self.assertEqual(
            2,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            1,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # 新建项目集
        self.assertEqual(0, team.projects(project_set=project_set, status=None).count())
        self.assertEqual(
            0,
            team.projects(
                project_set=project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            0,
            team.projects(
                project_set=project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # project2加入项目集，现在默认项目集有1个进行中，1个完成，新建项目集1个进行中
        project2.move_to_project_set(project_set)
        project2.reload()
        # 测试数量
        # 全部
        self.assertEqual(3, team.projects(status=None).count())
        self.assertEqual(2, team.projects(status=ProjectStatus.WORKING).count())
        self.assertEqual(1, team.projects(status=ProjectStatus.FINISHED).count())
        # 默认项目集
        self.assertEqual(
            2,
            team.projects(project_set=default_project_set, status=None).count(),
        )
        self.assertEqual(
            1,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            1,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # 新建项目集
        self.assertEqual(1, team.projects(project_set=project_set, status=None).count())
        self.assertEqual(
            1,
            team.projects(
                project_set=project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            0,
            team.projects(
                project_set=project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # project1 加入项目集
        project1.move_to_project_set(project_set)
        project1.reload()
        # 测试数量
        # 全部
        self.assertEqual(3, team.projects(status=None).count())
        self.assertEqual(2, team.projects(status=ProjectStatus.WORKING).count())
        self.assertEqual(1, team.projects(status=ProjectStatus.FINISHED).count())
        # 默认项目集
        self.assertEqual(
            1,
            team.projects(project_set=default_project_set, status=None).count(),
        )
        self.assertEqual(
            1,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            0,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # 新建项目集
        self.assertEqual(2, team.projects(project_set=project_set, status=None).count())
        self.assertEqual(
            1,
            team.projects(
                project_set=project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            1,
            team.projects(
                project_set=project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # project3 加入项目集，现在在新建项目集有2个进行中，1个完成
        project3.move_to_project_set(project_set)
        project3.reload()
        # 测试数量
        # 全部
        self.assertEqual(3, team.projects(status=None).count())
        self.assertEqual(2, team.projects(status=ProjectStatus.WORKING).count())
        self.assertEqual(1, team.projects(status=ProjectStatus.FINISHED).count())
        # 默认项目集
        self.assertEqual(
            0,
            team.projects(project_set=default_project_set, status=None).count(),
        )
        self.assertEqual(
            0,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            0,
            team.projects(
                project_set=default_project_set, status=ProjectStatus.FINISHED
            ).count(),
        )
        # 新建项目集
        self.assertEqual(3, team.projects(project_set=project_set, status=None).count())
        self.assertEqual(
            2,
            team.projects(
                project_set=project_set, status=ProjectStatus.WORKING
            ).count(),
        )
        self.assertEqual(
            1,
            team.projects(
                project_set=project_set, status=ProjectStatus.FINISHED
            ).count(),
        )

    def test_default_role(self):
        """测试默认角色"""
        user1 = User(name="u1", email="u1").save()
        team = Team.create("t1", user1)
        self.assertEqual(team.default_role.system_code, Team.default_role_system_code)

    def test_default_project_set(self):
        """测试默认项目集"""
        user1 = User(name="u1", email="u1").save()
        team1 = Team.create("t1", user1)
        self.assertEqual(
            DEFAULT_PROJECT_SETS_COUNT + 1, ProjectSet.objects.count()
        )  # 一共有1个
        self.assertEqual(1, team1.project_sets().count())
        self.assertIsNotNone(team1.default_project_set)
        self.assertEqual(True, team1.default_project_set.default)
        self.assertEqual("default", team1.default_project_set.name)
        self.assertEqual(team1.default_project_set, team1.project_sets().first())

        team2 = Team.create("t2", user1)
        self.assertEqual(
            DEFAULT_PROJECT_SETS_COUNT + 2, ProjectSet.objects.count()
        )  # 一共有2个
        self.assertEqual(1, team1.project_sets().count())
        self.assertEqual(1, team2.project_sets().count())
        self.assertIsNotNone(team1.default_project_set)
        self.assertIsNotNone(team2.default_project_set)
        self.assertEqual(True, team1.default_project_set.default)
        self.assertEqual(True, team2.default_project_set.default)
        self.assertEqual("default", team1.default_project_set.name)
        self.assertEqual("default", team2.default_project_set.name)
        self.assertNotEqual(team2.default_project_set, team1.default_project_set)

    def test_custom_role(self):
        """测试自定义角色"""
        with self.app.test_request_context():
            user1 = User(name="u1", email="u1").save()
            user2 = User(name="u2", email="u2").save()
            team1 = Team.create(name="t1")
            team2 = Team.create(name="t2")
            # 用错误的权限创建自定义角色，报错
            with self.assertRaises(PermissionNotExistError):
                team1.create_role("new_role", 101, [123456], intro="自建角色")
            # 创建自定义角色不影响其他团队
            new_role = team1.create_role("new_role", 101, [1], intro="自建角色")
            self.assertEqual(team1.roles().count(), team2.roles().count() + 1)
            # 用户1以member角色加入，level是100
            user1.join(team1)
            self.assertEqual(user1.get_team_relation(team1).role.level, 100)
            self.assertEqual(
                user1.get_team_relation(team1).role.system_code,
                team1.default_role_system_code,
            )
            # 用户2以新role加入，level是101
            user2.join(team1, new_role)
            self.assertEqual(user2.get_team_relation(team1).role.level, 101)
            self.assertEqual(user2.get_team_relation(team1).role.name, "new_role")
            # 用户2以新role加入team2，报错
            with self.assertRaises(RoleNotExistError):
                user2.join(team2, new_role)

    def test_clean(self):
        """测试mongoengine过滤"""
        team = Team.create("1")
        project_set = team.default_project_set
        with self.app.test_request_context():
            # 用错误的代码
            with self.assertRaises(ApplicationCheckTypeNotExistError):
                Project(
                    name="p1",
                    project_set=project_set,
                    source_language=Language.by_code("ja"),
                    application_check_type=999,
                    team=team,
                ).save()
            with self.assertRaises(AllowApplyTypeNotExistError):
                Project(
                    name="p1",
                    project_set=project_set,
                    source_language=Language.by_code("ja"),
                    allow_apply_type=999,
                    team=team,
                ).save()
            # 正确的创建
            project1 = Project(
                project_set=project_set,
                source_language=Language.by_code("ja"),
                name="p1",
                team=team,
            ).save()
            # 赋值时用错误的代码
            with self.assertRaises(ApplicationCheckTypeNotExistError):
                project1.application_check_type = 999
                project1.save()
            # 还原赋值
            project1.reload()
            with self.assertRaises(AllowApplyTypeNotExistError):
                project1.allow_apply_type = 999
                project1.save()

    def test_CASECAD(self):
        """测试和团队绑定的删除"""
        with self.app.test_request_context():
            user1 = User(name="u1", email="u1").save()
            user2 = User(name="u2", email="u2").save()
            user3 = User(name="u3", email="u3").save()
            user4 = User(name="u4", email="u4").save()
            # === 创建 team1 的第一组数据 ===
            team = Team.create(name="t1", creator=user1)
            team.allow_apply_type = AllowApplyType.ALL  # 允许所有人加入
            team.save()
            # 创建角色、用户
            role = team.create_role(name="r1", level=1, permissions=[1])
            user4.join(team, role)
            user1.invite(user2, team, role)
            user3.apply(team)
            # 创建术语库
            term_bank = TermBank.create(
                "u",
                team,
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
                user=user1,
            )
            Term.create(term_bank, "o", "t", user=user1)
            # 创建项目
            project = Project.create(
                name="p1",
                creator=user1,
                team=team,
                allow_apply_type=AllowApplyType.ALL,
            )
            target = project.targets().first()
            role = project.create_role(name="r1", level=1, permissions=[1])
            user4.join(project, role)
            user1.invite(user2, project, role)
            user3.apply(project)
            # 上传文件，term.txt会创建三条source
            with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as file:
                file = project.upload("term.txt", file)
            file_save_name = str(file.save_name)  # 保存文件名，用于后期查询
            # 增加两个翻译
            file.sources()[0].create_translation("test", target, user=user1)
            file.sources()[0].create_translation("test", target, user=user2)
            file.sources()[0].create_tip("test", target, user=user1)
            file.sources()[0].create_tip("test", target, user=user2)

            # === 创建 team1 的第二组数据（以检测删除不会影响其他团队） ===
            team2 = Team.create(name="t2", creator=user1)
            team2.allow_apply_type = AllowApplyType.ALL  # 允许所有人加入
            team2.save()
            # 创建角色、用户
            role = team2.create_role(name="r1", level=1, permissions=[1])
            user4.join(team2, role)
            user1.invite(user2, team2, role)
            user3.apply(team2)
            # 创建术语库
            term_bank = TermBank.create(
                "u",
                team2,
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
                user=user1,
            )
            Term.create(term_bank, "o", "t", user=user1)
            # 创建项目
            project2 = Project.create(
                name="p1",
                creator=user1,
                team=team2,
                allow_apply_type=AllowApplyType.ALL,
            )
            target = project2.targets().first()
            role = project2.create_role(name="r1", level=1, permissions=[1])
            user4.join(project2, role)
            user1.invite(user2, project2, role)
            user3.apply(project2)
            # 上传文件，term.txt会创建三条source
            with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as file:
                file = project2.upload("term.txt", file)
            file_save_name2 = str(file.save_name)  # 保存文件名，用于后期查询
            # 增加两个翻译
            file.sources()[0].create_translation("test", target, user=user1)
            file.sources()[0].create_translation("test", target, user=user2)
            file.sources()[0].create_tip("test", target, user=user1)
            file.sources()[0].create_tip("test", target, user=user2)

            # 这时候应该有（两个 team 数量是两倍）
            # 3个用户，1个团队，2个团队-用户关系（其中一个是自定义角色），1个自定义角色，1个术语库，1个术语，1个语言
            # 1个项目，2个团队-用户关系（其中一个是自定义角色），1个自定义角色，1个文件，3个原文，2个翻译，2个tip
            # 1个申请，1个邀请
            # 公用部分
            self.assertEqual(Language.objects().count(), 106)  # 语言不影响
            # 团队部分（team1）
            self.assertEqual(Team.objects.count(), DEFAULT_TEAMS_COUNT + 1 * 2)
            self.assertEqual(
                TeamUserRelation.objects.count(), DEFAULT_TEAM_USER_RELATIONS + 2 * 2
            )
            self.assertEqual(TeamRole.objects.count(), 5 + 1 * 2)  # 5个系统角色
            self.assertEqual(
                Application.objects(group__in=[team, team2]).count(), 1 * 2
            )
            self.assertEqual(Invitation.objects(group__in=[team, team2]).count(), 1 * 2)
            self.assertEqual(Project.objects.count(), 1 * 2)
            self.assertEqual(TermBank.objects.count(), 1 * 2)
            self.assertEqual(Term.objects.count(), 1 * 2)
            # 项目部分
            self.assertEqual(Project.objects.count(), 1 * 2)
            self.assertEqual(
                ProjectUserRelation.objects(group__in=[project, project2]).count(),
                2 * 2,
            )
            self.assertEqual(File.objects.count(), 1 * 2)
            self.assertEqual(Source.objects.count(), 3 * 2)
            self.assertEqual(Translation.objects.count(), 2 * 2)
            self.assertEqual(Tip.objects.count(), 2 * 2)
            self.assertEqual(
                ProjectRole.objects(group__in=[project, project2]).count(),
                1 * 2,
            )
            self.assertEqual(
                Application.objects(group__in=[project, project2]).count(),
                1 * 2,
            )
            self.assertEqual(
                Invitation.objects(group__in=[project, project2]).count(),
                1 * 2,
            )
            self.assertTrue(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name)
            )  # 文件1存在
            self.assertTrue(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name2)
            )  # 文件2存在
            # 这时候删除团队
            team.clear()
            # 这时候应该之剩下一半
            # 公用部分
            self.assertEqual(Language.objects().count(), 106)  # 语言不影响
            # 团队部分（team1）
            self.assertEqual(Team.objects.count(), DEFAULT_TEAMS_COUNT + 1)
            self.assertEqual(TeamUserRelation.objects.count(), DEFAULT_TEAM_USER_RELATIONS + 2)
            self.assertEqual(TeamRole.objects.count(), 5 + 1)  # 5个系统角色
            self.assertEqual(Application.objects(group__in=[team, team2]).count(), 1)
            self.assertEqual(Invitation.objects(group__in=[team, team2]).count(), 1)
            self.assertEqual(Application.objects(group__in=[team2]).count(), 1)
            self.assertEqual(Invitation.objects(group__in=[team2]).count(), 1)
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(TermBank.objects.count(), 1)
            self.assertEqual(Term.objects.count(), 1)
            # 项目部分
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(
                ProjectUserRelation.objects(group__in=[project, project2]).count(),
                2,
            )
            self.assertEqual(
                ProjectUserRelation.objects(group__in=[project2]).count(),
                2,
            )
            self.assertEqual(File.objects.count(), 1)
            self.assertEqual(Source.objects.count(), 3)
            self.assertEqual(Translation.objects.count(), 2)
            self.assertEqual(Tip.objects.count(), 2)
            self.assertEqual(
                ProjectRole.objects(group__in=[project, project2]).count(),
                1,
            )
            self.assertEqual(
                Application.objects(group__in=[project, project2]).count(),
                1,
            )
            self.assertEqual(
                Invitation.objects(group__in=[project, project2]).count(),
                1,
            )
            self.assertEqual(
                ProjectRole.objects(group__in=[project2]).count(),
                1,
            )
            self.assertEqual(
                Application.objects(group__in=[project2]).count(),
                1,
            )
            self.assertEqual(
                Invitation.objects(group__in=[project2]).count(),
                1,
            )
            self.assertFalse(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name)
            )  # 文件被删除了
            self.assertTrue(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name2)
            )  # 文件被删除了

    def test_permission(self):
        """测试权限是否有重复"""
        with self.app.test_request_context():
            names = dir(TeamPermission)
            values = [getattr(TeamPermission, name) for name in names if name.isupper()]
            for value in values:
                count = values.count(value)
                if count > 1:
                    raise AssertionError(f"权限有{count}个值为{value}, 请修改")
