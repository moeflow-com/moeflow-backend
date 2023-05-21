from app.models.project import Project, ProjectPermission, ProjectRole
from app.models.team import Team, TeamPermission, TeamRole
from app.models.user import User
from tests import DEFAULT_TEAMS_COUNT, MoeAPITestCase


class UserModelTestCase(MoeAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.create(name="1", email="1@1.com", password="123")

    def test_password(self):
        """密码设置与验证"""
        # 不能读取密码
        with self.assertRaises(AttributeError):
            self.user.password
        # 密码哈希存在值,且不是123
        self.assertIsNotNone(self.user.password_hash)
        self.assertNotEqual(self.user.password_hash, "123")
        # 验证密码
        self.assertTrue(self.user.verify_password("123"))
        self.assertFalse(self.user.verify_password("321"))

    def test_password_characteristic(self):
        """密码特征值生成与验证"""
        pc = self.user.password_characteristic
        # 验证密码特征
        self.assertTrue(self.user.verify_password_characteristic(pc))
        self.assertFalse(self.user.verify_password_characteristic("123"))
        # 设置新密码
        self.user.password = "321"
        pc1 = self.user.password_characteristic
        self.assertNotEqual(pc, pc1)
        # 验证密码特征
        self.assertFalse(self.user.verify_password_characteristic("123"))
        self.assertFalse(self.user.verify_password_characteristic(pc))
        self.assertTrue(self.user.verify_password_characteristic(pc1))

    def test_get_projects(self):
        """获取用户的项目"""
        team = Team.create("t1", creator=self.user)
        project1 = Project.create(name="p1", team=team)
        project2 = Project.create(name="p2", team=team)
        project3 = Project.create(name="p3", team=team)
        role1 = ProjectRole.objects(system_code="supporter").first()
        role2 = ProjectRole.objects(system_code="translator").first()
        self.user.join(project1, role1)
        self.user.join(project2, role1)
        self.user.join(project3, role2)
        self.assertEqual(len(self.user.projects(skip=1, limit=1)), 1)
        self.assertEqual(self.user.projects(skip=1, limit=1).first().name, "p2")
        self.assertEqual(self.user.projects().count(), 3)
        self.assertEqual(len(self.user.projects(role=role1)), 2)
        self.assertEqual(len(self.user.projects(role=role2)), 1)
        self.assertEqual(len(self.user.projects(role=[role1, role2])), 3)

    def test_get_teams(self):
        """获取用户的项目"""
        # 两个角色
        role1 = TeamRole.objects(system_code="beginner").first()
        role2 = TeamRole.objects(system_code="creator").first()
        # 三个团队
        team_default_role = TeamRole.by_system_code("beginner")
        team1 = Team.create("t1")
        team2 = Team.create("t2")
        team3 = Team.create("t3")
        team1.default_role = team_default_role
        team2.default_role = team_default_role
        team3.default_role = team_default_role
        # 用户加入三个团队
        self.user.join(team1, role1)
        self.user.join(team2, role1)
        self.user.join(team3, role2)
        # 获取用户所有teams，跳过并限制1
        self.assertEqual(len(self.user.teams(skip=1, limit=1)), 1)
        self.assertEqual(  # 第一个是默认团队
            "t2", self.user.teams(skip=DEFAULT_TEAMS_COUNT + 1, limit=1).first().name
        )
        # 用户加入了三个团队
        self.assertEqual(self.user.teams().count(), DEFAULT_TEAMS_COUNT + 3)
        self.assertEqual(len(self.user.teams(role=role1)), 2)
        self.assertEqual(len(self.user.teams(role=role2)), 1)
        self.assertEqual(len(self.user.teams(role=[role1, role2])), 3)

    def test_user_can(self):
        """测试can方法"""
        # team相关测试
        user = User(email="u1", name="u1").save()
        team = Team.create("t1")
        team2 = Team.create("t2")
        role = TeamRole.objects(system_code="beginner").first()
        user.join(team, role=role)
        self.assertTrue(user.can(team, TeamPermission.ACCESS))
        self.assertFalse(user.can(team, TeamPermission.DELETE))
        # 未加入的为False
        self.assertFalse(user.can(team2, TeamPermission.ACCESS))
        # project相关测试
        team3 = Team.create("t3")
        project = Project.create(name="p1", team=team3)
        project2 = Project.create(name="p2", team=team3)
        role = ProjectRole.objects(system_code="translator").first()
        user.join(project, role=role)
        self.assertTrue(user.can(project, ProjectPermission.ACCESS))
        self.assertFalse(user.can(project, ProjectPermission.DELETE))
        # 未加入的为False
        self.assertFalse(user.can(project2, ProjectPermission.ACCESS))

    def test_superior(self):
        """测试上下级"""
        # team相关测试
        leader = User(email="u1", name="u1").save()
        leader2 = User(email="u12", name="u12").save()
        member = User(email="u2", name="u2").save()
        team = Team.create("t1")
        leader_role = TeamRole.objects(system_code="creator").first()
        member_role = TeamRole.objects(system_code="beginner").first()
        leader.join(team, leader_role)
        leader2.join(team, leader_role)
        member.join(team, member_role)
        self.assertTrue(leader.is_superior(team, member))
        self.assertTrue(leader2.is_superior(team, member))
        self.assertFalse(member.is_superior(team, leader))
        self.assertFalse(leader2.is_superior(team, leader))
        # project相关测试
        project = Project.create(name="p1", team=Team.create("t2"))
        leader_role = ProjectRole.objects(system_code="creator").first()
        member_role = ProjectRole.objects(system_code="translator").first()
        leader.join(project, leader_role)
        leader2.join(project, leader_role)
        member.join(project, member_role)
        self.assertTrue(leader.is_superior(project, member))
        self.assertTrue(leader2.is_superior(project, member))
        self.assertFalse(member.is_superior(project, leader))
        self.assertFalse(leader2.is_superior(project, leader))

    def test_admin1(self):
        """测试创建新用户都没有管理员权限"""
        # team相关测试
        user = User.create(email="u1", name="u1", password="123123")
        self.assertFalse(user.admin)
        self.assertFalse(user.admin_can())

    def test_admin2(self):
        """测试有管理员权限"""
        # team相关测试
        user = User.create(email="u1", name="u1", password="123123")
        user.admin = True
        user.save()
        self.assertTrue(user.admin)
        self.assertTrue(user.admin_can())
