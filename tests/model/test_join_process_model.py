from app.core.rbac import AllowApplyType
from app.models.project import Project
from app.models.application import Application, ApplicationStatus
from app.models.invitation import Invitation, InvitationStatus
from app.models.team import Team, TeamRole
from app.models.user import User
from tests import MoeTestCase


class InviteApplyModelTestCase(MoeTestCase):
    def test_invite_base(self):
        # 获得role
        role_admin = TeamRole.by_system_code("admin")
        role_member = TeamRole.by_system_code("beginner")
        # 创建用户和团队
        user1 = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        user3 = User(name="u3", email="u3").save()
        team1 = Team.create(name="t1")
        team2 = Team.create(name="t2")
        # 把用户加入
        i1 = Invitation(
            user=user1, group=team1, message="", operator=user3, role=role_admin,
        ).save()
        i2 = Invitation(
            user=user2, group=team1, message="", operator=user3, role=role_member,
        ).save()
        # 使用Invitation的get方法获取邀请
        self.assertEqual(Invitation.get().count(), 2)
        self.assertEqual(Invitation.get(user=user1).count(), 1)
        self.assertEqual(Invitation.get(group=team1).count(), 2)
        # 使用GroupMixin和User类中获取邀请的方法
        self.assertEqual(team1.invitations().count(), 2)
        self.assertEqual(team2.invitations().count(), 0)
        self.assertEqual(user1.invitations().count(), 1)
        self.assertEqual(user2.invitations().count(), 1)
        self.assertEqual(user3.invitations().count(), 0)
        # 同意一个邀请,拒绝一个邀请
        i1.allow()
        i2.deny()
        # 用户1加入了,用户2没加入
        self.assertIsNotNone(user1.get_relation(team1))
        self.assertEqual(user1.get_relation(team1).role, role_admin)
        self.assertIsNone(user2.get_relation(team1))
        # 使用Invitation的get方法获取邀请
        self.assertEqual(Invitation.get().count(), 2)
        self.assertEqual(Invitation.get(user=user1).count(), 1)
        self.assertEqual(Invitation.get(group=team1).count(), 2)
        self.assertEqual(
            Invitation.get(group=team1, status=InvitationStatus.PENDING).count(), 0,
        )
        self.assertEqual(
            Invitation.get(group=team1, status=InvitationStatus.DENY).count(), 1,
        )
        self.assertEqual(
            Invitation.get(group=team1, status=InvitationStatus.ALLOW).count(), 1,
        )

    def test_apply_base(self):
        # 获得role
        role_admin = TeamRole.by_system_code("admin")
        role_member = TeamRole.by_system_code("beginner")
        # 创建用户和团队
        user1 = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        user3 = User(name="u3", email="u3").save()
        user4 = User(name="u4", email="u4").save()
        team_default_role = TeamRole.by_system_code("beginner")
        team1 = Team.create("t1")
        team2 = Team.create("t2")
        team1.default_role = team_default_role
        team2.default_role = team_default_role
        # 把用户加入
        a1 = Application(user=user1, group=team1, message="").save()
        a2 = Application(user=user2, group=team1, message="").save()
        a3 = Application(user=user3, group=team1, message="").save()
        # 使用Application的get方法获取邀请
        self.assertEqual(Application.get().count(), 3)
        self.assertEqual(Application.get(user=user1).count(), 1)
        self.assertEqual(Application.get(group=team1).count(), 3)
        # 使用GroupMixin和User类中获取邀请的方法
        self.assertEqual(team1.applications().count(), 3)
        self.assertEqual(team2.applications().count(), 0)
        self.assertEqual(user1.applications().count(), 1)
        self.assertEqual(user2.applications().count(), 1)
        self.assertEqual(user3.applications().count(), 1)
        # 同意一个邀请,拒绝一个邀请
        a1.allow(operator=user4)
        a2.deny(operator=user4)
        a3.allow(operator=user4, role=role_admin)  # 强制设置角色
        # 有操作者了
        self.assertEqual(a1.operator, user4)
        self.assertEqual(a2.operator, user4)
        # 用户1加入了,用户2没加入
        self.assertIsNotNone(user1.get_relation(team1))
        self.assertEqual(user1.get_relation(team1).role, role_member)
        self.assertIsNone(user2.get_relation(team1))
        self.assertIsNotNone(user3.get_relation(team1))
        self.assertEqual(user3.get_relation(team1).role, role_admin)
        # 使用Application的get方法获取邀请
        self.assertEqual(Application.get().count(), 3)
        self.assertEqual(Application.get(user=user1).count(), 1)
        self.assertEqual(Application.get(group=team1).count(), 3)
        self.assertEqual(
            Application.get(group=team1, status=ApplicationStatus.PENDING).count(), 0,
        )
        self.assertEqual(
            Application.get(group=team1, status=ApplicationStatus.DENY).count(), 1,
        )
        self.assertEqual(
            Application.get(group=team1, status=ApplicationStatus.ALLOW).count(), 2,
        )

    def test_related_applications(self):
        """
        测试获取自己可审核的加入申请
        """
        with self.app.test_request_context():
            user1 = User(name="u1", email="u1").save()
            user2 = User(name="u2", email="u2").save()
            user3 = User(name="u3", email="u3").save()
            user4 = User(name="u4", email="u4").save()
            user5 = User(name="u5", email="u5").save()
            user6 = User(name="u6", email="u6").save()
            user7 = User(name="u7", email="u7").save()
            User(name="u8", email="u8").save()  # 局外人
            team1 = Team.create("t1")
            project1 = Project.create(
                "p1", team=team1, creator=user1, allow_apply_type=AllowApplyType.ALL
            )
            user2.join(project1, role=project1.role_cls.by_system_code("admin"))
            user3.join(project1, role=project1.role_cls.by_system_code("coordinator"))
            user4.join(project1, role=project1.role_cls.by_system_code("proofreader"))
            user5.join(project1, role=project1.role_cls.by_system_code("translator"))
            user6.join(project1, role=project1.role_cls.by_system_code("supporter"))
            user7.apply(project1)
            application = Application.objects().first()
            # 只有 admin, creator, coordinator 被记录
            self.assertCountEqual(
                application.user_ids_can_check_user, [user1.id, user2.id, user3.id]
            )

