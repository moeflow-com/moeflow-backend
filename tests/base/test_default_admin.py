from app import create_app
from app.models.user import User
from tests import MoeTestCase


class TestDefaultAdmin(MoeTestCase):
    def test_create_default_admin_by_config(self):
        """测试自动创建默认管理员"""
        admin_user = User.objects.first()
        self.assertEqual(admin_user.email, self.app.config["ADMIN_EMAIL"])
        self.assertEqual(admin_user.admin, True)

    def test_reset_default_admin(self):
        """测试重启应用时，重置默认默认管理员权限"""
        admin_user = User.objects.first()
        user = self.create_user("user")
        self.assertEqual(admin_user.email, self.app.config["ADMIN_EMAIL"])
        self.assertEqual(admin_user.admin, True)
        admin_user.admin = False
        admin_user.save()
        admin_user.reload()
        self.assertEqual(admin_user.admin, False)
        create_app()
        admin_user.reload()
        self.assertEqual(admin_user.admin, True)
        # 测试其他用户权限不受影响
        user.reload()
        self.assertEqual(user.admin, False)

    def test_reset_default_admin_when_true(self):
        """测试重启应用时，但默认管理员已经是管理员，不会影响默认管理员权限"""
        admin_user = User.objects.first()
        user = self.create_user("user")
        self.assertEqual(admin_user.email, self.app.config["ADMIN_EMAIL"])
        self.assertEqual(admin_user.admin, True)
        self.assertEqual(user.admin, False)
        create_app()
        admin_user.reload()
        self.assertEqual(admin_user.admin, True)
        # 测试其他用户权限不受影响
        user.reload()
        self.assertEqual(user.admin, False)
