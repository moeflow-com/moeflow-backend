from app.models.user import User
from app.models.team import Team
from app.models.project import ProjectSet, Project
from app.models.file import File
from tests import MoeTestCase


class TestTestUtilsCase(MoeTestCase):
    """测试 测试帮助函数"""

    def test_create_user(self):
        self.create_user("user")

        # 测试数量
        self.assertEqual(User.objects.count(), 1)
        # 测试名称
        user = User.objects.first()
        self.assertEqual(user.name, "user")

    def test_create_team(self):
        self.create_team("team")

        # 测试数量
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        # 测试名称
        team = Team.objects.first()
        self.assertEqual(team.name, "team")
        user = User.objects.first()
        self.assertEqual(user.name, "team-creator")

    def test_create_project_set(self):
        self.create_project_set("project_set")

        # 测试数量
        self.assertEqual(ProjectSet.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        # 测试名称
        project_set = ProjectSet.objects(default=False).first()
        self.assertEqual(project_set.name, "project_set")
        team = Team.objects.first()
        self.assertEqual(team.name, "project_set-team")
        user = User.objects.first()
        self.assertEqual(user.name, "project_set-team-creator")

    def test_create_project(self):
        self.create_project("project")

        # 测试数量
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(ProjectSet.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        # 测试名称
        project = Project.objects.first()
        self.assertEqual(project.name, "project")
        project_set = ProjectSet.objects(default=False).first()
        self.assertEqual(project_set.name, "project-project_set")
        team = Team.objects.first()
        self.assertEqual(team.name, "project-project_set-team")
        user = User.objects.first()
        self.assertEqual(user.name, "project-project_set-team-creator")

    def test_create_file(self):
        with self.app.test_request_context():
            self.create_file("file.txt")

            # 测试数量
            self.assertEqual(File.objects.count(), 1)
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(ProjectSet.objects.count(), 2)
            self.assertEqual(Team.objects.count(), 1)
            self.assertEqual(User.objects.count(), 1)
            # 测试名称
            file = File.objects.first()
            self.assertEqual(file.name, "file.txt")
            project = Project.objects.first()
            self.assertEqual(project.name, "file.txt-project")
            project_set = ProjectSet.objects(default=False).first()
            self.assertEqual(project_set.name, "file.txt-project-project_set")
            team = Team.objects.first()
            self.assertEqual(team.name, "file.txt-project-project_set-team")
            user = User.objects.first()
            self.assertEqual(user.name, "file.txt-project-project_set-team-creator")

