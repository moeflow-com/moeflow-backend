from app.models.project import Project
from mongoengine import DoesNotExist

from app.exceptions import NoPermissionError, RoleNotExistError
from app.models.team import Team, TeamPermission, TeamRole
from app.models.user import User
from app.constants.role import RoleType
from tests import MoeTestCase


class RoleModelTestCase(MoeTestCase):
    def test_get_roles(self):
        """测试通过 rbac GroupMixin 类中 roles 方法获取角色"""
        with self.app.test_request_context():
            user = User(name="u1", email="u1").save()
            team = Team.create(name="t1")
            member_role = TeamRole.by_system_code("member")
            user.join(team, role=member_role)
            system_role_count = TeamRole.objects(system=True).count()
            self.assertEqual(system_role_count, team.roles(type=RoleType.ALL).count())
            self.assertEqual(
                system_role_count - 1,
                team.roles(type=RoleType.ALL, without_creator=True).count(),
            )
            self.assertEqual(
                system_role_count, team.roles(type=RoleType.SYSTEM).count()
            )
            self.assertEqual(
                system_role_count - 1,
                team.roles(type=RoleType.SYSTEM, without_creator=True).count(),
            )
            self.assertEqual(0, team.roles(type=RoleType.CUSTOM).count())
            # 创建一个自定义角色
            team.create_role(
                name="r1",
                level=99,
                permissions=[TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK],
                operator=user,
            )
            self.assertEqual(
                1 + system_role_count, team.roles(type=RoleType.ALL).count()
            )
            self.assertEqual(
                1 + system_role_count - 1,
                team.roles(type=RoleType.ALL, without_creator=True).count(),
            )
            self.assertEqual(
                system_role_count, team.roles(type=RoleType.SYSTEM).count()
            )
            self.assertEqual(
                system_role_count - 1,
                team.roles(type=RoleType.SYSTEM, without_creator=True).count(),
            )
            self.assertEqual(1, team.roles(type=RoleType.CUSTOM).count())

    def test_create_role_via_rbac(self):
        """测试通过 rbac GroupMixin 类中的 create_role 方法创建角色"""
        with self.app.test_request_context():
            user = User(name="u1", email="u1").save()
            team = Team.create(name="t1")
            # 将user以member加入 level=200
            member_role = TeamRole.by_system_code("member")
            relation = user.join(team, role=member_role)
            self.assertIsNotNone(relation)
            # 可以创建权限比自己低的角色
            role = team.create_role(
                name="r1",
                level=199,
                permissions=[TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK],
                operator=user,
            )
            self.assertEqual("r1", role.name)
            self.assertEqual(199, role.level)
            self.assertEqual(
                sorted([TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK]),
                sorted(role.permissions),
            )
            # 不能创建level比自己高的角色
            with self.assertRaises(NoPermissionError):
                team.create_role(
                    name="r2",
                    level=200,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    operator=user,
                )
            with self.assertRaises(NoPermissionError):
                team.create_role(
                    name="r3",
                    level=201,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    operator=user,
                )
            # 不能创建permissions比自己多的角色
            with self.assertRaises(NoPermissionError):
                team.create_role(
                    name="r4",
                    level=199,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.DELETE,
                    ],  # DELETE权限只有创建者才有
                    operator=user,
                )

    def test_edit_role_via_rbac(self):
        """测试通过 rbac GroupMixin 类中的 edit_role 方法修改角色"""
        with self.app.test_request_context():
            user = User(name="u1", email="u1").save()
            team = Team.create(name="t1")
            # 将user以member加入 level=200
            member_role = TeamRole.by_system_code("member")
            relation = user.join(team, role=member_role)
            self.assertIsNotNone(relation)
            # 可以创建权限比自己低的角色
            role = team.create_role(
                name="r1",
                level=99,
                permissions=[TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK],
                operator=user,
            )
            role.reload()
            self.assertEqual("r1", role.name)
            self.assertEqual(99, role.level)
            self.assertEqual(
                sorted([TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK]),
                sorted(role.permissions),
            )
            # 可以修改成权限比自己低的角色
            # 不能修改level比自己高的角色
            team.edit_role(
                id=str(role.id),
                name="r1-1",
                level=188,
                permissions=[TeamPermission.ACCESS, TeamPermission.CREATE_TERM],
                operator=user,
            )
            role.reload()
            self.assertEqual("r1-1", role.name)
            self.assertEqual(188, role.level)
            self.assertEqual(
                sorted([TeamPermission.ACCESS, TeamPermission.CREATE_TERM]),
                sorted(role.permissions),
            )
            # 不能修改level比自己高的角色
            with self.assertRaises(NoPermissionError):
                team.edit_role(
                    id=str(role.id),
                    name="r2",
                    level=200,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    operator=user,
                )
            with self.assertRaises(NoPermissionError):
                team.edit_role(
                    id=str(role.id),
                    name="r3",
                    level=201,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    operator=user,
                )
            # 不能修改permissions比自己多的角色
            with self.assertRaises(NoPermissionError):
                team.edit_role(
                    id=str(role.id),
                    name="r4",
                    level=199,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.DELETE,
                    ],  # DELETE权限只有创建者才有
                    operator=user,
                )
            self.assertEqual("r1-1", role.name)
            self.assertEqual(188, role.level)
            self.assertEqual(
                sorted([TeamPermission.ACCESS, TeamPermission.CREATE_TERM]),
                sorted(role.permissions),
            )
            # 系统角色找不到，不能编辑
            with self.assertRaises(RoleNotExistError):
                member_role = TeamRole.by_system_code("beginner")
                team.edit_role(
                    id=str(member_role.id),
                    name="r4",
                    level=99,
                    permissions=[
                        TeamPermission.ACCESS,
                        TeamPermission.DELETE,
                    ],  # DELETE权限只有创建者才有
                    operator=user,
                )

    def test_delete_role_via_rbac(self):
        """测试通过rbac GroupMixin类中的delete_role方法删除角色"""
        with self.app.test_request_context():
            user = User(name="u1", email="u1").save()
            user2 = User(name="u2", email="u2").save()
            team = Team.create(name="t1")
            # 将user以member加入 level=200
            member_role = TeamRole.by_system_code("member")
            relation = user.join(team, role=member_role)
            self.assertIsNotNone(relation)
            # 可以创建权限比自己低的角色
            role = team.create_role(
                name="r1",
                level=99,
                permissions=[
                    TeamPermission.ACCESS,
                    TeamPermission.CREATE_TERM_BANK,
                ],
                operator=user,
            )
            role.reload()
            self.assertEqual("r1", role.name)
            self.assertEqual(99, role.level)
            self.assertEqual(
                sorted([TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK]),
                sorted(role.permissions),
            )
            # 将团队默认角色设置成这个role
            member_role = TeamRole.by_system_code("beginner")
            self.assertEqual(member_role, team.default_role)
            team.default_role = role
            team.save()
            team.reload()
            self.assertEqual(role, team.default_role)
            # user2加入成这个角色
            relation2 = user2.join(team)  # 默认角色已经是role了
            self.assertEqual(role, relation2.role)
            # 删除角色
            team.delete_role(id=str(role.id))
            # 团队默认角色恢复成系统默认角色
            team.reload()
            self.assertEqual(Team.default_system_role(), team.default_role)
            # user2的角色变成系统默认角色
            relation2.reload()
            self.assertEqual(Team.default_system_role(), relation2.role)
            # role已经没了
            with self.assertRaises(DoesNotExist):
                role.reload()

            # 系统角色找不到，不能删除
            with self.assertRaises(RoleNotExistError):
                member_role = TeamRole.by_system_code("beginner")
                team.delete_role(id=str(member_role.id))
            with self.assertRaises(RoleNotExistError):
                member_role = TeamRole.by_system_code("creator")
                team.delete_role(id=str(member_role.id))

    def test_users_by_permission(self):
        """测试通过rbac GroupMixin类中的test_users_by_permission方法获取用户"""
        user = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        user3 = User(name="u3", email="u3").save()
        user4 = User(name="u4", email="u4").save()
        team = Team.create(name="t1", creator=user)
        project = Project.create(name="p1", creator=user, team=team)
        user2.join(project, role=project.role_cls.by_system_code("admin"))
        user3.join(project, role=project.role_cls.by_system_code("proofreader"))
        user4.join(project, role=project.role_cls.by_system_code("supporter"))
        # 四个用户可以访问
        self.assertCountEqual(
            project.users_by_permission(project.permission_cls.ACCESS),
            [user, user2, user3, user4],
        )
        # 三个用户可以校对
        self.assertCountEqual(
            project.users_by_permission(project.permission_cls.PROOFREAD_TRA),
            [user, user2, user3],
        )
        # 两个用户可以审核加入申请
        self.assertCountEqual(
            project.users_by_permission(project.permission_cls.CHECK_USER),
            [user, user2],
        )
