from app.exceptions.language import TargetAndSourceLanguageSameError
from app.tasks.output_project import output_project
from app.models.language import Language
from app.models.target import Target
from app.models.team import Team
from app.models.user import User
from app.models.project import Project
from app.models.output import Output
from app.models.file import Translation, Tip
from tests import MoeAPITestCase
from app.constants.output import OutputTypes
from app import oss


class TargetTestCase(MoeAPITestCase):
    def test_cascade(self):
        with self.app.test_request_context():
            self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            team = Team.create("t1")
            language = Language.by_code("ko")
            project = Project.create("p1", team=team)
            file = project.create_file("f.txt")
            source = file.create_source(content="c")
            target = Target.create(project=project, language=language)
            Translation.create("t", source=source, target=target, user=user)
            Tip.create("t", source=source, target=target, user=user)
            Output.create(
                project=project, target=target, user=user, type=OutputTypes.ALL
            )
            self.assertEqual(Target.objects().count(), 2)
            self.assertEqual(Translation.objects().count(), 1)
            self.assertEqual(Tip.objects().count(), 1)
            self.assertEqual(Output.objects().count(), 1)
            target.clear()
            self.assertEqual(Target.objects().count(), 1)
            self.assertEqual(Translation.objects().count(), 0)
            self.assertEqual(Tip.objects().count(), 0)
            self.assertEqual(Output.objects().count(), 0)

    def test_delete_real_files(self):
        with self.app.test_request_context():
            self.create_user("11", "1@1.com", "111111")
            user = User.objects(email="1@1.com").first()
            team = Team.create("t1")
            language1 = Language.by_code("ko")
            language2 = Language.by_code("zh-TW")
            project = Project.create("p1", team=team)
            target1 = Target.create(project=project, language=language1)
            target2 = Target.create(project=project, language=language2)
            target1_output1 = Output.create(
                project=project, target=target1, user=user, type=OutputTypes.ALL
            )
            target1_output2 = Output.create(
                project=project, target=target1, user=user, type=OutputTypes.ALL
            )
            target2_output1 = Output.create(
                project=project, target=target2, user=user, type=OutputTypes.ALL
            )
            target2_output2 = Output.create(
                project=project, target=target2, user=user, type=OutputTypes.ALL
            )
            output_project(str(target1_output1.id))
            output_project(str(target1_output2.id))
            output_project(str(target2_output1.id))
            output_project(str(target2_output2.id))
            target1_output1.reload()
            target1_output2.reload()
            target2_output1.reload()
            target2_output2.reload()
            self.assertTrue(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target1_output1.id)
                    + "/",
                    target1_output1.file_name,
                )
            )
            self.assertTrue(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target1_output2.id)
                    + "/",
                    target1_output2.file_name,
                )
            )
            self.assertTrue(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target2_output1.id)
                    + "/",
                    target2_output1.file_name,
                )
            )
            self.assertTrue(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target2_output2.id)
                    + "/",
                    target2_output2.file_name,
                )
            )
            Output.delete_real_files(target1.outputs())
            # target 1 的 output 已被删除
            self.assertFalse(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target1_output1.id)
                    + "/",
                    target1_output1.file_name,
                )
            )
            self.assertFalse(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target1_output2.id)
                    + "/",
                    target1_output2.file_name,
                )
            )
            # target 2 的 output 依旧存在
            self.assertTrue(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target2_output1.id)
                    + "/",
                    target2_output1.file_name,
                )
            )
            self.assertTrue(
                oss.is_exist(
                    self.app.config["OSS_OUTPUT_PREFIX"]
                    + str(target2_output2.id)
                    + "/",
                    target2_output2.file_name,
                )
            )

    def test_create_target_and_source_language_same_error(self):
        """
        创建目标语言时，目标语言不可和源语言一样
        """
        with self.app.test_request_context():
            team = Team.create("t1")
            language1 = Language.by_code("ko")
            project = Project.create("p1", team=team, source_language=language1)
            with self.assertRaises(TargetAndSourceLanguageSameError):
                Target.create(project=project, language=language1)
