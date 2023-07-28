from app.tasks.output_project import output_project
from app.models.output import Output
import os

from flask import current_app

from app import oss
from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.exceptions import (
    FolderNotExistError,
    PermissionNotExistError,
    RoleNotExistError,
)
from app.exceptions.language import TargetAndSourceLanguageSameError
from app.models.application import Application, ApplicationStatus
from app.models.file import File, Source, Tip, Translation
from app.models.invitation import Invitation
from app.models.language import Language
from app.models.project import (
    Project,
    ProjectPermission,
    ProjectRole,
    ProjectUserRelation,
)
from app.models.team import Team, TeamRole
from app.models.user import User
from app.constants.file import FileNotExistReason, FileType
from app.constants.project import ProjectStatus
from tests import TEST_FILE_PATH, MoeTestCase
from app.constants.output import OutputTypes


class ProjectModelTestCase(MoeTestCase):
    def test_create_project_limit(self):
        # 项目原语言和目标语言不能相同
        user = User.create(name="u1", email="u1", password="123456")
        with self.assertRaises(TargetAndSourceLanguageSameError):
            Project.create(
                name="t1",
                team=Team.create("t1", creator=user),
                source_language=Language.by_code("ja"),
                target_languages=Language.by_code("ja"),
            )

    def test_create_with_default_kwargs(self):
        """测试默认的创建属性"""
        team = Team.create("t1")
        project = Project.create(name="p1", team=team)
        self.assertEqual("p1", project.name)
        self.assertEqual(ProjectRole.by_system_code("translator"), project.default_role)
        self.assertEqual("", project.intro)
        self.assertEqual(team.default_project_set, project.project_set)
        self.assertEqual(AllowApplyType.NONE, project.allow_apply_type)
        self.assertEqual(
            ApplicationCheckType.ADMIN_CHECK, project.application_check_type
        )
        self.assertEqual(Language.by_code("ja"), project.source_language)
        self.assertEqual(Language.by_code("zh-CN"), project.targets().first().language)

    def test_join_leave_project(self):
        """测试加入/离开项目"""
        user1 = User.create(name="u1", email="u1", password="123456")
        user2 = User.create(name="u2", email="u2", password="123456")
        project = Project.create(name="t1", team=Team.create("t1", creator=user1))
        # 加入了一位
        user1.join(project, role=ProjectRole.by_system_code("creator"))
        users = project.users()
        self.assertIsNotNone(user1.get_relation(project))
        self.assertIsNone(user2.get_relation(project))
        self.assertTrue(user1 in users)
        self.assertFalse(user2 in users)
        self.assertEqual(users.count(), 1)
        # 加入了两位
        user2.join(project, role=ProjectRole.by_system_code("admin"))
        users = project.users()
        self.assertTrue(user1 in users)
        self.assertTrue(user2 in users)
        self.assertEqual(users.count(), 2)
        # 离开了一位
        user2.leave(project)
        users = project.users()
        self.assertTrue(user1 in users)
        self.assertFalse(user2 in users)
        self.assertEqual(users.count(), 1)

    def test_change_role(self):
        """测试改变项目角色"""
        user = User.create(name="u1", email="u1", password="123456")
        project = Project.create(name="t1", team=Team.create("t1", creator=user))
        role1 = ProjectRole.objects.first()
        role2 = ProjectRole.objects.skip(1).first()
        user.join(project, role=role1)
        self.assertIsNotNone(user.get_relation(project))
        self.assertEqual(user.get_role(project), role1)
        user.set_role(project, role2)
        self.assertEqual(user.get_role(project), role2)

    def test_get_users(self):
        """测试获取项目用户"""
        user1 = User.create(name="u1", email="u1", password="123456")
        user2 = User.create(name="u2", email="u2", password="123456")
        user3 = User.create(name="u3", email="u3", password="123456")
        project = Project.create(name="t1", team=Team.create("t1", creator=user1))
        role1 = ProjectRole.objects(system_code="supporter").first()
        role2 = ProjectRole.objects(system_code="translator").first()
        user1.join(project, role1)
        user2.join(project, role1)
        user3.join(project, role2)
        project.users(role=role1)
        self.assertEqual(len(project.users(skip=1, limit=1)), 1)
        self.assertEqual(project.users(skip=1, limit=1).first().name, "u2")
        self.assertEqual(project.users().count(), 3)
        self.assertEqual(len(project.users(role=role1)), 2)
        self.assertEqual(len(project.users(role=role2)), 1)
        self.assertEqual(len(project.users(role=[role1, role2])), 3)

    def test_default_role(self):
        """测试自定义角色"""
        with self.app.test_request_context():
            user1 = User.create(name="u1", email="u1", password="123456")
            user2 = User.create(name="u2", email="u2", password="123456")
            team = Team.create("t1", creator=user1)
            project1 = Project.create(name="t1", team=team)
            project2 = Project.create(name="t2", team=team)
            # 用错误的权限创建自定义角色，报错
            with self.assertRaises(PermissionNotExistError):
                project1.create_role("new_role", 101, [123456], intro="自建角色")
            # 创建自定义角色不影响其他团队
            new_role = project1.create_role("new_role", 101, [1], intro="自建角色")
            self.assertEqual(project1.roles().count(), project2.roles().count() + 1)
            # 用户1以member角色加入，level是100
            user1.join(project1)
            self.assertEqual(user1.get_project_relation(project1).role.level, 200)
            self.assertEqual(
                user1.get_project_relation(project1).role.system_code,
                project1.default_role_system_code,
            )
            # 用户2以新role加入，level是101
            user2.join(project1, new_role)
            self.assertEqual(user2.get_project_relation(project1).role.level, 101)
            self.assertEqual(user2.get_project_relation(project1).role.name, "new_role")
            # 用户2以新role加入project2，报错
            with self.assertRaises(RoleNotExistError):
                user2.join(project2, new_role)

    def test_CASECAD(self):
        """测试和项目绑定的删除"""
        with self.app.test_request_context():
            system_roles_count = len(ProjectRole.system_role_data)
            user1 = User.create(name="u1", email="u1", password="123456")
            user2 = User.create(name="u2", email="u2", password="123456")
            user3 = User.create(name="u3", email="u3", password="123456")
            user4 = User.create(name="u4", email="u4", password="123456")
            project = Project.create(
                name="p1",
                creator=user1,
                team=Team.create("t1", creator=user1),
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
            # 增加2个output
            output1 = Output.create(
                project=project, target=target, user=user1, type=OutputTypes.ALL
            )
            output2 = Output.create(
                project=project, target=target, user=user1, type=OutputTypes.ALL
            )
            output_project(str(output1.id))
            output_project(str(output2.id))
            output1.reload()
            output2.reload()
            # 这时候应该有
            # 3个用户，1个项目，2个团队-用户关系（其中一个是自定义角色），1个自定义角色，
            # 1个文件，3个原文，2个翻译，2个tip，2个output，1个邀请，1个申请
            self.assertEqual(len(project.roles()), system_roles_count + 1)
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(ProjectUserRelation.objects(group=project).count(), 2)
            self.assertEqual(File.objects.count(), 1)
            self.assertEqual(Source.objects.count(), 3)
            self.assertEqual(Translation.objects.count(), 2)
            self.assertEqual(Tip.objects.count(), 2)
            self.assertEqual(ProjectRole.objects(group=project).count(), 1)
            self.assertEqual(Application.objects(group=project).count(), 1)
            self.assertEqual(Invitation.objects(group=project).count(), 1)
            self.assertTrue(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name)
            )
            self.assertTrue(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output1.id) + "/",
                    output1.file_name,
                )
            )
            self.assertTrue(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output2.id) + "/",
                    output2.file_name,
                )
            )
            # 这时候删除项目
            project.clear()
            # 这时候应该都没了
            self.assertEqual(ProjectRole.objects.count(), system_roles_count)
            self.assertEqual(Project.objects.count(), 0)
            self.assertEqual(ProjectUserRelation.objects().count(), 0)
            self.assertEqual(File.objects.count(), 0)
            self.assertEqual(Source.objects.count(), 0)
            self.assertEqual(Translation.objects.count(), 0)
            self.assertEqual(Tip.objects.count(), 0)
            self.assertEqual(ProjectRole.objects(group=project).count(), 0)
            self.assertEqual(Application.objects().count(), 0)
            self.assertEqual(Invitation.objects().count(), 0)
            self.assertFalse(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name)
            )
            self.assertFalse(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output1.id) + "/",
                    output1.file_name,
                )
            )
            self.assertFalse(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output2.id) + "/",
                    output2.file_name,
                )
            )

    def test_get_role(self):
        """测试获取role函数"""
        user1 = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        user3 = User(name="u3", email="u3").save()
        user4 = User(name="u4", email="u4").save()

        team = Team.create("t1")
        project = Project.create("p1", team, creator=user2)

        # user1是team的管理员
        user1.join(team, TeamRole.by_system_code("admin"))
        # 自动变成旗下项目的管理员
        self.assertEqual(ProjectRole.by_system_code("admin"), user1.get_role(project))

        # user2是team的管理员，也是project的创建者
        user2.join(team, TeamRole.by_system_code("admin"))
        # 获取角色是创建者
        self.assertEqual(ProjectRole.by_system_code("creator"), user2.get_role(project))

        # user3是team的成员，也是project的管理员
        user3.join(team, TeamRole.by_system_code("beginner"))
        user3.join(project, ProjectRole.by_system_code("admin"))
        # 获取角色是管理员
        self.assertEqual(ProjectRole.by_system_code("admin"), user3.get_role(project))

        # user4是team的成员，不是project的成员
        user4.join(team, TeamRole.by_system_code("beginner"))
        # 获取角色是None
        self.assertEqual(None, user4.get_role(project))

    def test_permission(self):
        """测试权限是否有重复"""
        with self.app.test_request_context():
            names = dir(ProjectPermission)
            values = [
                getattr(ProjectPermission, name) for name in names if name.isupper()
            ]
            for value in values:
                count = values.count(value)
                if count > 1:
                    raise AssertionError(f"权限有{count}个值为{value}, 请修改")

    def test_finish(self):
        """测试和项目绑定的删除"""
        with self.app.test_request_context():
            system_roles_count = len(ProjectRole.system_role_data)
            user1 = User.create(name="u1", email="u1", password="123456")
            user2 = User.create(name="u2", email="u2", password="123456")
            user3 = User.create(name="u3", email="u3", password="123456")
            user4 = User.create(name="u4", email="u4", password="123456")
            project = Project.create(
                name="p1",
                creator=user1,
                team=Team.create("t1", creator=user1),
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
            # 增加2个output
            output1 = Output.create(
                project=project, target=target, user=user1, type=OutputTypes.ALL
            )
            output2 = Output.create(
                project=project, target=target, user=user1, type=OutputTypes.ALL
            )
            output_project(str(output1.id))
            output_project(str(output2.id))
            output1.reload()
            output2.reload()
            # 这时候应该有
            # 3个用户，1个项目，2个团队-用户关系（其中一个是自定义角色），1个自定义角色，
            # 1个文件，3个原文，2个翻译，2个tip，2个output，1个邀请，1个申请
            self.assertEqual(len(project.roles()), system_roles_count + 1)
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(ProjectUserRelation.objects(group=project).count(), 2)
            self.assertEqual(File.objects.count(), 1)
            self.assertEqual(Source.objects.count(), 3)
            self.assertEqual(Translation.objects.count(), 2)
            self.assertEqual(Tip.objects.count(), 2)
            self.assertEqual(Output.objects.count(), 2)
            self.assertEqual(ProjectRole.objects(group=project).count(), 1)
            self.assertEqual(Application.objects(group=project).count(), 1)
            self.assertEqual(Invitation.objects(group=project).count(), 1)
            # 项目状态
            self.assertEqual(ProjectStatus.WORKING, project.status)
            self.assertIsNone(project.system_finish_time)
            self.assertIsNone(project.plan_finish_time)
            self.assertIsNone(project.plan_delete_time)
            self.assertTrue(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name)
            )
            self.assertTrue(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output1.id) + "/",
                    output1.file_name,
                )
            )
            self.assertTrue(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output2.id) + "/",
                    output2.file_name,
                )
            )
            self.assertTrue(file.save_name)
            # 这时候完结项目
            project.plan_finish()
            project.finish()
            # 项目状态发生变化
            self.assertEqual(ProjectStatus.FINISHED, project.status)
            self.assertIsNotNone(project.system_finish_time)
            self.assertIsNotNone(project.plan_finish_time)
            self.assertIsNone(project.plan_delete_time)
            # 文件被删除了
            self.assertFalse(
                oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file_save_name)
            )
            self.assertFalse(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output1.id) + "/",
                    output1.file_name,
                )
            )
            self.assertFalse(
                oss.is_exist(
                    current_app.config["OSS_OUTPUT_PREFIX"] + str(output2.id) + "/",
                    output2.file_name,
                )
            )
            # 文件的状态变化了
            file.reload()
            self.assertFalse(file.save_name)
            self.assertEqual(FileNotExistReason.FINISH, file.file_not_exist_reason)
            # 其他数据库记录没有变化
            self.assertEqual(len(project.roles()), system_roles_count + 1)
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(ProjectUserRelation.objects(group=project).count(), 2)
            self.assertEqual(File.objects.count(), 1)
            self.assertEqual(Source.objects.count(), 3)
            self.assertEqual(Translation.objects.count(), 2)
            self.assertEqual(Tip.objects.count(), 2)
            self.assertEqual(Output.objects.count(), 2)
            self.assertEqual(ProjectRole.objects(group=project).count(), 1)
            self.assertEqual(Application.objects(group=project).count(), 1)
            self.assertEqual(Invitation.objects(group=project).count(), 1)

    def test_files(self):
        """
        测试获取项目下文件
        """
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
                team = Team.create("t1")
                # 另一个项目
                project_out = Project.create("po", team=team)
                dir_out = project_out.create_folder("diro")
                file_out = project_out.upload("fo.txt", file)
                self.assertEqual(2, project_out.files().count())
                # 本项目
                project = Project.create("p1", team=team)
                dir1 = project.create_folder("dir1")
                dir2 = project.create_folder("dir2", parent=dir1)
                file2 = project.upload("f2.txt", file, parent=dir1)
                file1 = project.upload("f1.txt", file)

                # 测试无条件搜索
                self.assertEqual(4, project.files().count())

                # 测试只搜索文件
                files = project.files(type_exclude=FileType.FOLDER)
                self.assertEqual(2, files.count())
                self.assertEqual(
                    sorted(["f1.txt", "f2.txt"]),
                    sorted([f.name for f in files]),
                )

                # 测试只搜索文件夹
                files = project.files(type_only=FileType.FOLDER)
                self.assertEqual(2, files.count())
                self.assertEqual(
                    sorted(["dir1", "dir2"]), sorted([f.name for f in files])
                )

                # 测试搜索文件夹内
                files = project.files(parent=None)
                self.assertEqual(2, files.count())
                self.assertEqual(
                    sorted(["dir1", "f1.txt"]), sorted([f.name for f in files])
                )

                files = project.files(parent=dir1)
                self.assertEqual(2, files.count())
                self.assertEqual(
                    sorted(["dir2", "f2.txt"]), sorted([f.name for f in files])
                )

                files = project.files(parent=dir2)
                self.assertEqual(0, files.count())

                # 测试限制
                files = project.files(skip=1, limit=2)
                self.assertEqual(4, files.count())
                self.assertEqual(2, len(files))
                self.assertEqual(
                    sorted(["dir2", "f1.txt"]), sorted([f.name for f in files])
                )

                # 测试排序
                files = project.files()
                self.assertEqual(
                    ["dir1", "f1.txt", "dir2", "f2.txt"],
                    [f.name for f in files],
                )
                files = project.files(order_by=["-dir_sort_name", "-sort_name"])
                self.assertEqual(
                    ["f2.txt", "dir2", "f1.txt", "dir1"],
                    [f.name for f in files],
                )
                files = project.files(order_by=["_id"])  # 按创建顺序
                self.assertEqual(
                    ["dir1", "dir2", "f2.txt", "f1.txt"],
                    [f.name for f in files],
                )

                # 错误的parent
                with self.assertRaises(FolderNotExistError):
                    files = project.files(parent=dir_out)
                with self.assertRaises(FolderNotExistError):
                    files = project.files(parent=file_out)
                with self.assertRaises(FolderNotExistError):
                    files = project.files(parent=file1)
                with self.assertRaises(FolderNotExistError):
                    files = project.files(parent=file2)

    def test_create_folder(self):
        """测试通过函数创建folder"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
                team = Team.create("t1")
                # 另一个项目
                project_out = Project.create("po", team=team)
                dir_out = project_out.create_folder("diro")
                file_out = project_out.upload("fo.txt", file)
                self.assertEqual(2, project_out.files().count())
                # 本项目
                project = Project.create("p1", team=team)
                dir1 = project.create_folder("dir1")
                project.create_folder("dir2", parent=dir1)
                file1 = project.upload("f1.txt", file)
                self.assertEqual(3, project.files().count())
                # 尝试在错误的parent创建
                with self.assertRaises(FolderNotExistError):
                    project.create_folder("diro1", parent=dir_out)
                with self.assertRaises(FolderNotExistError):
                    project.create_folder("diro1", parent=file_out)
                with self.assertRaises(FolderNotExistError):
                    project.create_folder("diro1", parent=file1)
                self.assertEqual(3, project.files().count())
                self.assertEqual(2, project_out.files().count())

    def test_upload(self):
        """测试通过函数上传文件"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
                team = Team.create("t1")
                # 另一个项目
                project_out = Project.create("po", team=team)
                dir_out = project_out.create_folder("diro")
                file_out = project_out.upload("fo.txt", file)
                self.assertEqual(2, project_out.files().count())
                # 本项目
                project = Project.create("p1", team=team)
                dir1 = project.create_folder("dir1")
                self.assertEqual(1, project.files().count())
                # 上传文件
                file1 = project.upload("f1.txt", file)
                file2 = project.upload("f2.txt", file, parent=dir1)
                self.assertEqual(3, project.files().count())
                # 尝试在错误的parent上传
                with self.assertRaises(FolderNotExistError):
                    project.upload("fo.txt", file, parent=dir_out)
                with self.assertRaises(FolderNotExistError):
                    project.upload("fo.txt", file, parent=file_out)
                with self.assertRaises(FolderNotExistError):
                    project.upload("fo.txt", file, parent=file1)
                with self.assertRaises(FolderNotExistError):
                    project.upload("fo.txt", file, parent=file2)
                self.assertEqual(3, project.files().count())
                self.assertEqual(2, project_out.files().count())

    def test_to_labelplus(self):
        """测试导出labelplus"""
        with self.app.test_request_context():
            # 创建一个测试项目
            user1 = User.create(name="1", email="1@1.com", password="123456")
            user2 = User.create(name="2", email="2@1.com", password="123456")
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            user1.join(project, Project.role_cls.by_system_code("proofreader"))
            user2.join(project, Project.role_cls.by_system_code("proofreader"))
            # 创建文件
            file0 = project.create_file("file0.png")  # 此文件没有原文
            file1 = project.create_file("file1.png")
            f1 = project.create_folder("f1")
            f2 = project.create_folder("f2", parent=f1)
            file2 = project.create_file("file2.jpg", parent=f2)
            file3 = project.create_file("file3.txt")
            # 创建原文/翻译
            default_target = project.targets().first()
            # file1
            source1 = file1.create_source("f1s1", x=0.11111, y=0.22222)
            source2 = file1.create_source("f1s2", x=0.99999, y=0.123456789)
            source3 = file1.create_source("f1s3", x=1, y=0)  # 空原文
            source1.create_translation("f1t1-1", target=default_target, user=user1)
            source1.create_translation(  # 这个新创建，输出这个
                "f1t1-new", target=default_target, user=user2
            )
            f1t2select = source2.create_translation(  # 这个被select，输出这个
                "f1t2-select", target=default_target, user=user1
            )
            source2.create_translation("f1t2-2", target=default_target, user=user2)
            f1t2select.select(user1)
            # file2
            source3 = file2.create_source("f2s1")
            source4 = file2.create_source("f2s2")
            f2t1 = source3.create_translation("f2t1", target=default_target, user=user2)
            f2t1.proofread_content = "f2t1-proofread"
            f2t1.proofreader = user1
            f2t1.save()
            source4.create_translation("f2t2", target=default_target, user=user2)
            # file3 文本文件，不会输出
            source5 = file3.create_source("f3s1")
            source6 = file3.create_source("f3s2")
            source5.create_translation("f3t1", target=default_target, user=user2)
            source6.create_translation("f3t2", target=default_target, user=user2)
            # 对比生成的labelplus
            need_result = (
                "1,0\r\n"
                + "-\r\n"
                + "框内\r\n"
                + "框外\r\n"
                + "-\r\n"
                + "可使用 LabelPlus Photoshop 脚本导入 psd 中\r\n"
                + ">>>>>>>>[file0.png]<<<<<<<<\r\n"
                + ">>>>>>>>[file1.png]<<<<<<<<\r\n"
                + "----------------[1]----------------[0.11111,0.22222,1]\r\n"
                + "f1t1-new\r\n"
                + "----------------[2]----------------[0.99999,0.123456789,1]\r\n"  # noqa: E501
                "f1t2-select\r\n"
                + "----------------[3]----------------[1.0,0.0,1]\r\n"
                + "\r\n"
                + ">>>>>>>>[f1/f2/file2.jpg]<<<<<<<<\r\n"
                + "----------------[1]----------------[0.0,0.0,1]\r\n"
                + "f2t1-proofread\r\n"
                + "----------------[2]----------------[0.0,0.0,1]\r\n"
                + "f2t2\r\n"
            )
            result = project.to_labelplus(target=default_target)
            self.assertEqual(need_result, result)

    def test_apply_auto_become_project_team1(self):
        """
        测试团队管理员申请后自动成为项目管理员
        - 即使关闭申请也可以加入
        """
        with self.app.test_request_context():
            # 创建一个测试项目
            user1 = User.create(name="1", email="1@1.com", password="123456")
            team = Team.create("t1")
            project = Project.create(
                "p1", team=team, allow_apply_type=AllowApplyType.NONE
            )
            # 加入成团队管理员
            user1.join(team, role=TeamRole.by_system_code("admin"))
            self.assertIsNone(user1.get_relation(project))
            # 用户申请后直接加入
            user1.apply(project)
            relation = user1.get_relation(project)
            self.assertIsNotNone(relation)
            self.assertEqual(ProjectRole.by_system_code("admin"), relation.role)

    def test_apply_auto_become_project_team2(self):
        """
        测试团队管理员申请后自动成为项目管理员
        - 加入后自动取消之前的申请
        """
        with self.app.test_request_context():
            # 创建一个测试项目
            user1 = User.create(name="1", email="1@1.com", password="123456")
            team = Team.create("t1")
            project = Project.create(
                "p1", team=team, allow_apply_type=AllowApplyType.ALL
            )
            # 加入前申请
            user1.apply(project)
            self.assertEqual(1, user1.applications(group=project).count())  # 总共有一个
            self.assertEqual(
                1,
                user1.applications(
                    group=project, status=ApplicationStatus.PENDING
                ).count(),
            )
            # 加入成团队管理员
            user1.join(team, role=TeamRole.by_system_code("admin"))
            self.assertIsNone(user1.get_relation(project))
            # 用户申请后直接加入
            user1.apply(project)
            relation = user1.get_relation(project)
            self.assertIsNotNone(relation)
            self.assertEqual(ProjectRole.by_system_code("admin"), relation.role)
            self.assertEqual(0, user1.applications(group=project).count())

    def test_apply_auto_become_project_team3(self):
        """
        测试团队管理员申请后自动成为项目管理员
        - 加入后自动取消之前的邀请
        """
        with self.app.test_request_context():
            # 创建一个测试项目
            user1 = User.create(name="1", email="1@1.com", password="123456")
            user2 = User.create(name="2", email="2@2.com", password="123456")
            team = Team.create("t1")
            project = Project.create(
                "p1", team=team, allow_apply_type=AllowApplyType.ALL, creator=user2
            )
            # 加入前邀请
            user2.invite(user1, project, role=ProjectRole.by_system_code("translator"))
            self.assertEqual(1, user1.invitations(group=project).count())  # 总共有一个
            self.assertEqual(
                1,
                user1.invitations(
                    group=project, status=ApplicationStatus.PENDING
                ).count(),
            )
            self.assertEqual(
                ProjectRole.by_system_code("translator"),
                user1.invitations(group=project, status=ApplicationStatus.PENDING)
                .first()
                .role,
            )
            # 加入成团队管理员
            user1.join(team, role=TeamRole.by_system_code("admin"))
            self.assertIsNone(user1.get_relation(project))
            # 用户申请后直接加入，切角色不受之前邀请影响
            user1.apply(project)
            relation = user1.get_relation(project)
            self.assertIsNotNone(relation)
            self.assertEqual(ProjectRole.by_system_code("admin"), relation.role)
            self.assertEqual(
                0,
                user1.invitations(group=project).count(),
            )
