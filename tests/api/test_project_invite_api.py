from app.exceptions import (
    InvitationFinishedError,
    NoPermissionError,
    TargetIsFullError,
)
from app.models.invitation import Invitation, InvitationStatus
from app.models.project import Project, ProjectPermission, ProjectRole
from app.models.team import Team, TeamRole
from app.models.user import User
from tests import MoeAPITestCase


class JoinProcessAPITestCase(MoeAPITestCase):
    def test_project_invite1(self):
        """
        user1(局外人)邀请user2(成为成员)加入project1, user1没权限
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team = Team.create("t1")
        project1 = Project.create("p1", team=team)
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        ProjectRole.by_system_code("admin")
        ProjectRole.by_system_code("creator")
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)

    def test_project_invite2(self):
        """
        user1(普通成员)邀请user2(成为成员)加入project1, user1没权限
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        ProjectRole.by_system_code("admin")
        ProjectRole.by_system_code("creator")
        # user1 加入为普通成员
        user1.join(project1)
        self.assertEqual(user1.get_relation(project1).role, member_role)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)

    def test_project_invite3(self):
        """
        user1(创建者)邀请user2(成为成员)加入project1, user2同意
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        ProjectRole.by_system_code("admin")
        creator_role = ProjectRole.by_system_code("creator")
        # user1 加入为创建者
        user1.join(project1, role=creator_role)
        self.assertEqual(user1.get_relation(project1).role, creator_role)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 有一个pending邀请
        self.assertEqual(Invitation.objects(status=InvitationStatus.PENDING).count(), 1)
        # user2同意这个邀请
        invitation = Invitation.objects().first()
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": True},
            token=token2,
        )
        self.assertErrorEqual(data)
        # user2加入了project1，并且是成员权限
        self.assertEqual(user2.get_relation(project1).role, member_role)
        # Invitation变成ALLOW
        invitation.reload()
        self.assertEqual(invitation.status, InvitationStatus.ALLOW)

    def test_project_invite4(self):
        """
        user1(创建者)邀请user2(成为成员)加入project1, user2拒绝，然后再邀请，user2同意
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        ProjectRole.by_system_code("admin")
        creator_role = ProjectRole.by_system_code("creator")
        # user1 加入为创建者
        user1.join(project1, role=creator_role)
        self.assertEqual(user1.get_relation(project1).role, creator_role)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 有一个pending邀请
        self.assertEqual(Invitation.objects(status=InvitationStatus.PENDING).count(), 1)
        # user2拒绝这个邀请
        invitation = Invitation.objects(status=InvitationStatus.PENDING).first()
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": False},
            token=token2,
        )
        self.assertErrorEqual(data)
        # user2没加入project1
        self.assertEqual(user2.get_relation(project1), None)
        # Invitation变成DENY
        invitation.reload()
        self.assertEqual(invitation.status, InvitationStatus.DENY)
        # 这时候能继续邀请
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 又新增了一个邀请
        self.assertEqual(Invitation.objects(status=InvitationStatus.PENDING).count(), 1)
        self.assertEqual(Invitation.objects(status=InvitationStatus.DENY).count(), 1)
        # user2同意这个邀请
        invitation = Invitation.objects(status=InvitationStatus.PENDING).first()
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": True},
            token=token2,
        )
        self.assertErrorEqual(data)
        # user2加入了project1，并且是成员权限
        self.assertEqual(user2.get_relation(project1).role, member_role)
        # Invitation变成ALLOW
        self.assertEqual(Invitation.objects(status=InvitationStatus.ALLOW).count(), 1)
        self.assertEqual(Invitation.objects(status=InvitationStatus.DENY).count(), 1)

    def test_project_invite5(self):
        """
        user1(创建者)邀请user2(成为成员)加入project1, user2拒绝/同意，此时此邀请不能再操作
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        ProjectRole.by_system_code("admin")
        creator_role = ProjectRole.by_system_code("creator")
        # user1 加入为创建者
        user1.join(project1, role=creator_role)
        self.assertEqual(user1.get_relation(project1).role, creator_role)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 有一个pending邀请
        self.assertEqual(Invitation.objects(status=InvitationStatus.PENDING).count(), 1)
        # user2拒绝这个邀请
        invitation = Invitation.objects().first()
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": False},
            token=token2,
        )
        self.assertErrorEqual(data)
        # user2没加入project1
        self.assertEqual(user2.get_relation(project1), None)
        # Invitation变成DENY
        invitation.reload()
        self.assertEqual(invitation.status, InvitationStatus.DENY)
        # user2再同意这个邀请，报错不能进行操作
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": True},
            token=token2,
        )
        self.assertErrorEqual(data, InvitationFinishedError)
        self.assertEqual(Invitation.objects(status=InvitationStatus.DENY).count(), 1)
        # 再次邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual(Invitation.objects(status=InvitationStatus.DENY).count(), 1)
        self.assertEqual(Invitation.objects(status=InvitationStatus.PENDING).count(), 1)
        # user2同意
        invitation = Invitation.objects(status=InvitationStatus.PENDING).first()
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": True},
            token=token2,
        )
        self.assertErrorEqual(data)
        self.assertEqual(Invitation.objects(status=InvitationStatus.DENY).count(), 1)
        self.assertEqual(Invitation.objects(status=InvitationStatus.ALLOW).count(), 1)
        # 此时这个ALLOW的邀请也不能操作
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": False},
            token=token2,
        )
        self.assertErrorEqual(data, InvitationFinishedError)

    def test_project_invite6(self):
        """
        user1(管理员)邀请user2(成为管理员)加入project1, user1没权限
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")
        admin_role = ProjectRole.by_system_code("admin")
        ProjectRole.by_system_code("creator")
        # user1 加入为管理员
        user1.join(project1, admin_role)
        self.assertEqual(user1.get_relation(project1).role, admin_role)
        # 邀请user2成为管理员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(admin_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)

    def test_project_invite7(self):
        """
        user1(管理员)邀请user2(成为创建者)加入project1, user1没权限
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")
        admin_role = ProjectRole.by_system_code("admin")
        creator_role = ProjectRole.by_system_code("creator")
        # user1 加入为管理员
        user1.join(project1, admin_role)
        self.assertEqual(user1.get_relation(project1).role, admin_role)
        # 邀请user2成为创始人
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(creator_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)

    def test_project_invite8(self):
        """
        项目特别测试1
        user1(管理员)邀请user2(成为成员)加入project1, user2是project1所在team的成员，自动加入
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        team1 = Team.create("t1")
        project1 = Project.create("p1", team=team1)
        user2.join(team1)  # user2是project1所在team的成员
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        admin_role = ProjectRole.by_system_code("admin")
        ProjectRole.by_system_code("creator")
        # user1 加入为管理员
        user1.join(project1, admin_role)
        self.assertEqual(user1.get_relation(project1).role, admin_role)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # user2已经加入了project
        self.assertEqual(user2.get_relation(project1).role, member_role)

    def test_change_project_invite1(self):
        """
        修改项目邀请权限
        先修改成和自己一样、比自己大，报错
        再修改成两个比自己小的，成功，最终加入是最后修改成功的角色
        同意之后不能再修改
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")  # 100
        test_role1 = project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        test_role2 = project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        creator_role = ProjectRole.by_system_code("creator")  # 500
        # user1 加入为test_role2
        user1.join(project1, test_role2)
        self.assertEqual(user1.get_relation(project1).role, test_role2)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 邀请里角色是成员
        invitation = Invitation.objects.first()
        self.assertEqual(invitation.role, member_role)
        # 修改角色为test_role2，报错
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(test_role2.id)},
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)
        invitation.reload()
        self.assertEqual(invitation.role, member_role)  # 仍然是成员角色
        # 修改角色为creator_role，报错
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(creator_role.id)},
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)
        invitation.reload()
        self.assertEqual(invitation.role, member_role)  # 仍然是成员角色
        # 修改角色为test_role1
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(test_role1.id)},
            token=token1,
        )
        self.assertErrorEqual(data)
        invitation.reload()
        self.assertEqual(invitation.role, test_role1)
        # 修改角色为admin_role
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(admin_role.id)},
            token=token1,
        )
        self.assertErrorEqual(data)
        invitation.reload()
        self.assertEqual(invitation.role, admin_role)
        # user2同意，角色变成admin_role
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": True},
            token=token2,
        )
        self.assertErrorEqual(data)
        # user2加入了project1，并且是成员权限
        self.assertEqual(user2.get_relation(project1).role, admin_role)
        # 同意之后不能修改
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(test_role1.id)},
            token=token1,
        )
        self.assertErrorEqual(data, InvitationFinishedError)

    def test_change_project_invite2(self):
        """
        修改团队邀请权限
        不能修改比自己大的角色邀请的比自己大的角色的用户
        拒绝之后不能再修改
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        token3 = self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")  # 100
        test_role1 = project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        test_role2 = project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        creator_role = ProjectRole.by_system_code("creator")  # 500
        # user1 加入为creator_role
        # user2 加入为admin_role
        user1.join(project1, creator_role)
        user2.join(project1, admin_role)
        self.assertEqual(user1.get_relation(project1).role, creator_role)
        self.assertEqual(user2.get_relation(project1).role, admin_role)
        # user1邀请user3成为test_role2
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user3.id),
                "role_id": str(test_role2.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 邀请里角色是成员
        invitation = Invitation.objects.first()
        self.assertEqual(invitation.role, test_role2)
        # user2尝试修改user3角色为test_role2，报错
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(test_role1.id)},
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # user2尝试修改user3角色为admin_role，报错
        data2 = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(admin_role.id)},
            token=token2,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # 两个报错一致，都是因为此用户等级高
        self.assertEqual(data.json, data2.json)
        # user3拒绝
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": False},
            token=token3,
        )
        self.assertErrorEqual(data)
        # 拒绝之后不能修改
        data = self.put(
            f"/v1/invitations/{invitation.id}",
            json={"role_id": str(test_role1.id)},
            token=token1,
        )
        self.assertErrorEqual(data, InvitationFinishedError)

    def test_delete_project_invite1(self):
        """
        用户删除没有权限
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        token4 = self.create_user("44", "4@4.com", "111111").generate_token()
        user4 = User.by_name("44")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [1])
        admin_role = ProjectRole.by_system_code("admin")  # 400
        test_role2 = project1.create_role("tr2", 450, [ProjectPermission.INVITE_USER])
        creator_role = ProjectRole.by_system_code("creator")  # 500
        # user1 加入为creator_role
        # user2 加入为admin_role
        # user4 加入为member_role
        user1.join(project1, creator_role)
        user2.join(project1, admin_role)
        user4.join(project1, member_role)
        self.assertEqual(user1.get_relation(project1).role, creator_role)
        self.assertEqual(user2.get_relation(project1).role, admin_role)
        # user1邀请user3成为test_role2
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user3.id),
                "role_id": str(test_role2.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        # 邀请里角色是成员
        invitation = Invitation.objects.first()
        self.assertEqual(invitation.role, test_role2)
        # user4尝试删除，user4没有删除邀请权限
        data = self.delete(f"/v1/invitations/{invitation.id}", token=token4)
        self.assertErrorEqual(data, NoPermissionError)
        # user2尝试删除，邀请的用户等级高，不能删除
        data1 = self.delete(f"/v1/invitations/{invitation.id}", token=token2)
        self.assertErrorEqual(data, NoPermissionError)
        # 两个不一样
        self.assertNotEqual(data.json["message"], data1.json["message"])
        # user1可以删除成功
        data = self.delete(f"/v1/invitations/{invitation.id}", token=token1)
        self.assertEqual(Invitation.objects.count(), 0)

    def test_user_full(self):
        """测试用户满时不能邀请"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        self.create_user("33", "3@3.com", "111111").generate_token()
        user3 = User.by_name("33")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 设置project1为一个人
        project1.max_user = 1
        project1.save()
        # 获取一些常用的role
        ProjectRole.by_system_code("translator")  # 100
        project1.create_role("tr1", 150, [ProjectPermission.INVITE_USER])
        ProjectRole.by_system_code("admin")  # 200
        test_role2 = project1.create_role("tr2", 250, [ProjectPermission.INVITE_USER])
        creator_role = ProjectRole.by_system_code("creator")  # 300
        # user1 加入为creator_role, 现在一个人，不能加入
        user1.join(project1, creator_role)
        self.assertEqual(user1.get_relation(project1).role, creator_role)
        # user1邀请user3成为test_role2
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(test_role2.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, TargetIsFullError)
        # user3 加入，现在两个人，还是不能加入
        user3.join(project1)
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(test_role2.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, TargetIsFullError)

    def test_project_invite9(self):
        """
        项目特别测试2
        user1(团队管理员，非project成员)邀请user2(成为成员)加入project1
        """
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.by_name("11")
        token2 = self.create_user("22", "2@2.com", "111111").generate_token()
        user2 = User.by_name("22")
        project1 = Project.create("p1", team=Team.create("t1", creator=user1))
        # 获取一些常用的role
        member_role = ProjectRole.by_system_code("translator")
        admin_role = ProjectRole.by_system_code("admin")
        ProjectRole.by_system_code("creator")
        # user1 get_role返回的是管理员角色
        self.assertEqual(admin_role, user1.get_role(project1))
        self.assertIsNone(user2.get_role(project1))
        self.assertEqual(
            TeamRole.by_system_code("creator"),
            user1.get_role(Team.create("t2", creator=user1)),
        )
        # 邀请user2成为管理员，报错
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(admin_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # 邀请user2成为成员
        data = self.post(
            f"/v1/projects/{project1.id}/invitations",
            json={
                "user_id": str(user2.id),
                "role_id": str(member_role.id),
                "message": "i1",
            },
            token=token1,
        )
        self.assertErrorEqual(data)
        self.assertEqual(1, Invitation.objects.count())
        invitation = Invitation.objects.first()
        # user2同意，角色变成member_role
        data = self.patch(
            f"/v1/invitations/{invitation.id}",
            json={"allow": True},
            token=token2,
        )
        self.assertErrorEqual(data)
        # user2加入了project1，并且是成员权限
        self.assertEqual(member_role, user2.get_relation(project1).role)
        # user1仍然没有关系
        self.assertIsNone(user1.get_relation(project1))
