from app.core.rbac import AllowApplyType, ApplicationCheckType
from app.exceptions import (
    ApplicationFinishedError,
    NoPermissionError,
    TargetIsFullError,
)
from app.models.application import Application, ApplicationStatus
from app.models.project import (
    Project,
    ProjectAllowApplyType,
    ProjectPermission,
    ProjectRole,
)
from app.models.team import Team, TeamRole
from app.models.user import User
from tests import DEFAULT_USERS_COUNT, MoeAPITestCase


class JoinProcessAPITestCase(MoeAPITestCase):
    def test_project_apply1(self):
        """
        user1申请加入project1
        团队默认不允许申请加入
        """
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置项目加入方式
        self.assertEqual(AllowApplyType.NONE, project1.allow_apply_type)
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        # user1 加入为 管理员
        user1.join(project1, admin_role)
        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        self.assertEqual(0, Application.objects.count())

    def test_project_apply2(self):
        """
        user1申请加入project1
        任何人可以加入的项目, user1拒绝
        同时测试 申请完成后不能删除
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        token3 = self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置项目加入方式
        project1.allow_apply_type = AllowApplyType.ALL
        project1.save()
        self.assertEqual(AllowApplyType.ALL, project1.allow_apply_type)
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        # user1 加入为 管理员
        # user3 加入为 成员
        user1.join(project1, admin_role)
        user3.join(project1, member_role)
        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Application.objects.count())
        application = Application.objects.first()
        # user3和user2都没有权限拒绝
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": False}, token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": False}, token=token3,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # user1 有权限拒绝
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": False}, token=token1,
        )
        self.assertErrorEqual(data)
        # 申请变成deny
        application.reload()
        self.assertEqual(ApplicationStatus.DENY, application.status)
        # 用户没有加入团队
        self.assertEqual(user2.get_relation(project1), None)
        # 失败的邀请不能再删除
        data = self.delete(f"/v1/applications/{application.id}", token=token2)
        self.assertErrorEqual(data, ApplicationFinishedError)

    def test_project_apply3(self):
        """
        user1申请加入project1
        任何人可以加入的项目, user1同意后加入
        同时测试 申请完成后不能删除
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        token3 = self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置项目加入方式
        project1.allow_apply_type = AllowApplyType.ALL
        project1.save()
        self.assertEqual(AllowApplyType.ALL, project1.allow_apply_type)
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        # user1 加入为 管理员
        # user3 加入为 成员
        user1.join(project1, admin_role)
        user3.join(project1, member_role)
        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Application.objects.count())
        application = Application.objects.first()
        # user3和user2都没有权限同意
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": True}, token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": True}, token=token3,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # user1 有权限同意
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": True}, token=token1,
        )
        self.assertErrorEqual(data)
        # 申请变成allow
        application.reload()
        self.assertEqual(ApplicationStatus.ALLOW, application.status)
        # 用户加入了团队
        self.assertEqual(user2.get_relation(project1).role, project1.default_role)
        # 成功加入的邀请不能再删除
        data = self.delete(f"/v1/applications/{application.id}", token=token2)
        self.assertErrorEqual(data, ApplicationFinishedError)

    def test_project_apply4(self):
        """
        user1申请加入project1
        仅申请人本人可以删除申请
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        token3 = self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置项目加入方式
        project1.allow_apply_type = AllowApplyType.ALL
        project1.save()
        self.assertEqual(AllowApplyType.ALL, project1.allow_apply_type)
        self.assertEqual(
            ApplicationCheckType.ADMIN_CHECK, project1.application_check_type
        )
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        # user1 加入为 管理员
        # user3 加入为 成员
        user1.join(project1, admin_role)
        user3.join(project1, member_role)
        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Application.objects.count())
        application = Application.objects.first()
        # user1和user3都没有权限删除
        data = self.delete(f"/v1/applications/{application.id}", token=token1)
        self.assertErrorEqual(data, NoPermissionError)
        data = self.delete(f"/v1/applications/{application.id}", token=token3)
        self.assertErrorEqual(data, NoPermissionError)
        self.assertEqual(1, Application.objects.count())
        # user2本人可以删除
        data = self.delete(f"/v1/applications/{application.id}", token=token2)
        self.assertErrorEqual(data)
        self.assertEqual(0, Application.objects.count())
        self.assertEqual(1, Project.objects.count())
        self.assertEqual(DEFAULT_USERS_COUNT + 3, User.objects.count())

    def test_project_apply5(self):
        """
        user1申请加入project1
        无需审核的项目可以直接加入
        """
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置项目加入方式
        project1.allow_apply_type = AllowApplyType.ALL
        project1.application_check_type = ApplicationCheckType.NO_NEED_CHECK
        project1.save()
        self.assertEqual(AllowApplyType.ALL, project1.allow_apply_type)
        self.assertEqual(
            ApplicationCheckType.NO_NEED_CHECK, project1.application_check_type
        )
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        # user1 加入为 管理员
        # user3 加入为 成员
        user1.join(project1, admin_role)
        user3.join(project1, member_role)
        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Application.objects.count())
        application = Application.objects.first()
        # 无需审核
        # 申请变成allow
        application.reload()
        self.assertEqual(ApplicationStatus.ALLOW, application.status)
        # 用户加入了团队
        self.assertEqual(user2.get_relation(project1).role, project1.default_role)

    def test_user_full(self):
        """测试用户满时不能邀请"""
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置项目加入方式
        project1.max_user = 1
        project1.allow_apply_type = AllowApplyType.ALL
        project1.save()
        self.assertEqual(AllowApplyType.ALL, project1.allow_apply_type)
        self.assertEqual(
            ApplicationCheckType.ADMIN_CHECK, project1.application_check_type
        )
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        # user1 加入为 管理员
        # user3 加入为 成员
        user1.join(project1, admin_role)
        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data, TargetIsFullError)
        # user2 加入，现在两个人，还是不能加入
        user3.join(project1)
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data, TargetIsFullError)

    def test_project_apply6(self):
        """
        project特别测试：
        project1属于team1只允许团队用户加入，且需要审核
        user2（团队用户）申请加入project1，user3（非团队用户）申请加入project1
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        token3 = self.create_user("33", "3@3.com", "111111").generate_token()
        team1 = Team.create("t1")
        project1 = Project.create("p1", team=team1)
        # 设置项目加入方式
        project1.allow_apply_type = ProjectAllowApplyType.TEAM_USER
        project1.application_check_type = ApplicationCheckType.ADMIN_CHECK
        project1.save()
        self.assertEqual(ProjectAllowApplyType.TEAM_USER, project1.allow_apply_type)
        self.assertEqual(
            ApplicationCheckType.ADMIN_CHECK, project1.application_check_type
        )
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        team_member_role = TeamRole.by_system_code("beginner")
        # user1 加入为 管理员
        # user1、user2 加入为 团队 成员
        user1.join(project1, admin_role)
        user1.join(team1, team_member_role)
        user2.join(team1, team_member_role)

        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Application.objects.count())
        application = Application.objects.first()
        # user1 有权限同意
        data = self.patch(
            f"/v1/applications/{application.id}", json={"allow": True}, token=token1,
        )
        self.assertErrorEqual(data)
        # 申请变成allow
        application.reload()
        self.assertEqual(ApplicationStatus.ALLOW, application.status)
        # 用户加入了团队
        self.assertEqual(user2.get_relation(project1).role, project1.default_role)

        # user3 申请加入，报错
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token3,
        )
        self.assertErrorEqual(data, NoPermissionError)

    def test_project_apply7(self):
        """
        project特别测试：
        project1属于team1只允许团队用户加入，且需要审核
        user2（团队用户）申请加入project1，user3（非团队用户）申请加入project1
        """
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        token3 = self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        team1 = Team.create("t1")
        project1 = Project.create("p1", team=team1)
        # 设置项目加入方式
        project1.allow_apply_type = ProjectAllowApplyType.TEAM_USER
        project1.application_check_type = ApplicationCheckType.NO_NEED_CHECK
        project1.save()
        self.assertEqual(ProjectAllowApplyType.TEAM_USER, project1.allow_apply_type)
        self.assertEqual(
            ApplicationCheckType.NO_NEED_CHECK, project1.application_check_type
        )
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("creator")  # 500
        team_member_role = TeamRole.by_system_code("beginner")
        # user1 加入为 管理员
        # user1、user2 加入为 团队 成员
        user1.join(project1, admin_role)
        user1.join(team1, team_member_role)
        user2.join(team1, team_member_role)

        # user2 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Application.objects.count())
        application = Application.objects.first()

        # 无需审核
        # 申请变成allow
        application.reload()
        self.assertEqual(ApplicationStatus.ALLOW, application.status)
        # 用户加入了团队
        self.assertEqual(user2.get_relation(project1).role, project1.default_role)

        # user3 申请加入，报错
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token3,
        )
        self.assertErrorEqual(data, NoPermissionError)

        # user3 加入了团队后可以直接加入
        user3.join(team1, team_member_role)
        # user3 申请加入
        data = self.post(
            f"/v1/projects/{project1.id}/applications",
            json={"message": "hi"},
            token=token3,
        )
        self.assertErrorEqual(data)
        self.assertEqual(2, Application.objects.count())
        application = Application.objects.first()

        # 无需审核
        # 申请变成allow
        application.reload()
        self.assertEqual(ApplicationStatus.ALLOW, application.status)
        # 用户加入了团队
        self.assertEqual(user3.get_relation(project1).role, project1.default_role)
