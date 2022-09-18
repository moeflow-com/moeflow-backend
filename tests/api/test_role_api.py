from mongoengine import DoesNotExist

from app.exceptions import NeedTokenError, NoPermissionError, RoleNotExistError
from app.models.team import Team, TeamPermission, TeamRole
from app.models.user import User
from app.constants.role import RoleType
from flask_apikit.exceptions import ValidateError
from tests import MoeAPITestCase


class RoleAPITestCase(MoeAPITestCase):
    def test_get_role(self):
        """测试通过api获取role"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            User.objects(email="2@1.com").first()
            team = Team.create(name="t1")
            member_role = TeamRole.by_system_code("member")
            user.join(team, role=member_role)
            # 创建一个role
            team.create_role(
                name="r1",
                level=99,
                permissions=[TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK],
                operator=user,
            )
            # == 没有登录时，不能获取 ==
            data = self.get(f"/v1/teams/{str(team.id)}/roles")
            self.assertErrorEqual(data, NeedTokenError)
            # == 没有权限，不能获取 ==
            data = self.get(f"/v1/teams/{str(team.id)}/roles", token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 正常获取 ==
            data = self.get(f"/v1/teams/{str(team.id)}/roles", token=token)
            self.assertErrorEqual(data)
            system_role_count = TeamRole.objects(system=True).count()
            self.assertEqual(
                system_role_count + 1, int(data.headers.get("X-Pagination-Count")),
            )

    def test_create_role(self):
        """测试通过api创建role"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            User.objects(email="2@1.com").first()
            team = Team.create(name="t1")
            admin_role = TeamRole.by_system_code("admin")
            user.join(team, role=admin_role)
            self.assertEqual(0, team.roles(type=RoleType.CUSTOM).count())
            # == 没有登录时，不能创建 ==
            data = self.post(f"/v1/teams/{str(team.id)}/roles", json={})
            self.assertErrorEqual(data, NeedTokenError)
            # == 没有权限，不能创建 ==
            data = self.post(f"/v1/teams/{str(team.id)}/roles", json={}, token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 缺少参数无法创建 ==
            data = self.post(f"/v1/teams/{str(team.id)}/roles", json={}, token=token)
            self.assertErrorEqual(data, ValidateError)
            # == level超出范围，无法创建 ==
            data = self.post(
                f"/v1/teams/{str(team.id)}/roles",
                json={
                    "name": "1",
                    "level": -1,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            data = self.post(
                f"/v1/teams/{str(team.id)}/roles",
                json={
                    "name": "1",
                    "level": 9999,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            # == permissions超出范围，无法创建 ==
            data = self.post(
                f"/v1/teams/{str(team.id)}/roles",
                json={
                    "name": "1",
                    "level": 1,
                    "permissions": [TeamPermission.ACCESS, TeamPermission.DELETE,],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 正常创建 ==
            data = self.post(
                f"/v1/teams/{str(team.id)}/roles",
                json={
                    "name": "1",
                    "level": 1,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, team.roles(type=RoleType.CUSTOM).count())

    def test_edit_role(self):
        """测试通过api修改role"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            User.objects(email="2@1.com").first()
            team = Team.create(name="t1")
            admin_role = TeamRole.by_system_code("admin")
            user.join(team, role=admin_role)
            self.assertEqual(0, team.roles(type=RoleType.CUSTOM).count())
            # == 创建一个角色 ==
            role = team.create_role(
                name="99", level=99, permissions=[TeamPermission.ACCESS], operator=user,
            )
            self.assertEqual("99", role.name)
            self.assertEqual(99, role.level)
            self.assertEqual(sorted([TeamPermission.ACCESS]), sorted(role.permissions))
            # == 没有登录时，不能修改 ==
            data = self.put(f"/v1/teams/{str(team.id)}/roles/{str(role.id)}", json={})
            self.assertErrorEqual(data, NeedTokenError)
            # == 没有权限，不能修改 ==
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}", json={}, token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 系统权限，不能修改（不能被找到） ==
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(admin_role.id)}",
                json={
                    "name": "1",
                    "level": 1,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, RoleNotExistError)
            # == 缺少参数无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}", json={}, token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            # == level超出范围，无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}",
                json={
                    "name": "1",
                    "level": -1,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}",
                json={
                    "name": "1",
                    "level": 9999,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            # == permissions超出范围，无法修改 ==
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}",
                json={
                    "name": "1",
                    "level": 1,
                    "permissions": [TeamPermission.ACCESS, TeamPermission.DELETE,],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 正常修改 ==
            data = self.put(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}",
                json={
                    "name": "1",
                    "level": 1,
                    "permissions": [
                        TeamPermission.ACCESS,
                        TeamPermission.CREATE_TERM_BANK,
                    ],
                    "intro": "",
                },
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(1, team.roles(type=RoleType.CUSTOM).count())
            role.reload()
            self.assertEqual("1", role.name)
            self.assertEqual(1, role.level)
            self.assertEqual(
                sorted([TeamPermission.ACCESS, TeamPermission.CREATE_TERM_BANK]),
                sorted(role.permissions),
            )

    def test_delete_role(self):
        """测试通过api修改role"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@1.com", "111111").generate_token()
            User.objects(email="2@1.com").first()
            team = Team.create(name="t1")
            admin_role = TeamRole.by_system_code("admin")
            user.join(team, role=admin_role)
            self.assertEqual(0, team.roles(type=RoleType.CUSTOM).count())
            # == 创建一个角色 ==
            role = team.create_role(
                name="99", level=99, permissions=[TeamPermission.ACCESS], operator=user,
            )
            self.assertEqual("99", role.name)
            self.assertEqual(99, role.level)
            self.assertEqual(sorted([TeamPermission.ACCESS]), sorted(role.permissions))
            self.assertEqual(1, team.roles(type=RoleType.CUSTOM).count())
            # == 没有登录时，不能删除 ==
            data = self.delete(f"/v1/teams/{str(team.id)}/roles/{str(role.id)}")
            self.assertErrorEqual(data, NeedTokenError)
            # == 没有权限，不能删除 ==
            data = self.delete(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}", token=token2
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 系统权限，不能删除（不能被找到） ==
            data = self.delete(
                f"/v1/teams/{str(team.id)}/roles/{str(admin_role.id)}", token=token,
            )
            self.assertErrorEqual(data, RoleNotExistError)
            # == 正常删除 ==
            data = self.delete(
                f"/v1/teams/{str(team.id)}/roles/{str(role.id)}", token=token
            )
            self.assertEqual(0, team.roles(type=RoleType.CUSTOM).count())
            # role已经没了
            with self.assertRaises(DoesNotExist):
                role.reload()
