from app.exceptions.base import NoPermissionError
from tests import MoeAPITestCase


class AdminAPITestCase(MoeAPITestCase):
    def test_admin_admin_status_api(self):
        """管理员用户可以修改管理员状态"""
        admin_user = self.create_user("admin")
        admin_user.admin = True
        admin_user.save()
        admin_token = admin_user.generate_token()
        # Admin can enable admin status
        user = self.create_user("user")
        token = user.generate_token()
        self.assertFalse(user.admin)
        data = self.put(
            "/v1/admin/admin-status",
            json={"user_id": str(user.id), "status": True},
            token=admin_token,
        )
        self.assertErrorEqual(data)
        user.reload()
        self.assertTrue(user.admin)
        # Admin can disable admin status
        data = self.put(
            "/v1/admin/admin-status",
            json={"user_id": str(user.id), "status": False},
            token=admin_token,
        )
        self.assertErrorEqual(data)
        user.reload()
        self.assertFalse(user.admin)
        # Non-admin cannot edit admin status
        data = self.put(
            "/v1/admin/admin-status",
            json={"user_id": str(user.id), "status": True},
            token=token,
        )
        self.assertErrorEqual(data, NoPermissionError)
