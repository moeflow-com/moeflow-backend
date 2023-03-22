from app.models.user import User
from app.models.team import Team
from app.models.project import ProjectSet, Project
from app.models.file import File
from tests import DEFAULT_USERS_COUNT, MoeTestCase


class TestTestUtilsCase(MoeTestCase):
    """测试 测试帮助函数"""

    def test_create_user(self):
        self.create_user("user")

        # 测试数量
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # 测试名称
        self.assertIsNotNone(User.get_by_email('user@test.com'))

    def test_create_team(self):
        self.create_team("team")

        # 测试数量
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # 测试名称
        team = Team.objects.first()
        self.assertEqual(team.name, "team")
        self.assertIsNotNone(User.get_by_email('team-creator@test.com'))

    def test_create_project_set(self):
        self.create_project_set("project_set")

        # 测试数量
        self.assertEqual(ProjectSet.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # 测试名称
        project_set = ProjectSet.objects(default=False).first()
        self.assertEqual(project_set.name, "project_set")
        team = Team.objects.first()
        self.assertEqual(team.name, "project_set-team")
        self.assertIsNotNone(User.get_by_email('project_set-team-creator@test.com'))

    def test_create_project(self):
        self.create_project("project")

        # 测试数量
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(ProjectSet.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # 测试名称
        project = Project.objects.first()
        self.assertEqual(project.name, "project")
        project_set = ProjectSet.objects(default=False).first()
        self.assertEqual(project_set.name, "project-project_set")
        team = Team.objects.first()
        self.assertEqual(team.name, "project-project_set-team")
        self.assertIsNotNone(User.get_by_email('project-project_set-team-creator@test.com'))

    def test_create_file(self):
        with self.app.test_request_context():
            self.create_file("file.txt")

            # 测试数量
            self.assertEqual(File.objects.count(), 1)
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(ProjectSet.objects.count(), 2)
            self.assertEqual(Team.objects.count(), 1)
            self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
            # 测试名称
            file = File.objects.first()
            self.assertEqual(file.name, "file.txt")
            project = Project.objects.first()
            self.assertEqual(project.name, "file.txt-project")
            project_set = ProjectSet.objects(default=False).first()
            self.assertEqual(project_set.name, "file.txt-project-project_set")
            team = Team.objects.first()
            self.assertEqual(team.name, "file.txt-project-project_set-team")
            self.assertIsNotNone(User.get_by_email('file.txt-project-project_set-team-creator@test.com'))

