import io
import os
from zipfile import ZipFile

from app import oss
from app.constants.output import OutputTypes
from app.models.language import Language
from tests import TEST_FILE_PATH, MoeAPITestCase


class OutputAPITestCase(MoeAPITestCase):
    def test_output_project1(self):
        """测试导出项目全部内容（含图片）"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            project.upload("1.png", file)
            project.upload("2.png", file)
            project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={"type": OutputTypes.ALL},
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_zip_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".zip"
        )
        output_zip = ZipFile(io.BytesIO(output_zip_in_oss.read()))
        output_zip_namelist = output_zip.namelist()
        # self.assertIn("ps_script.jsx", output_zip_namelist)
        self.assertIn("translations.txt", output_zip_namelist)
        self.assertIn("images/1.png", output_zip_namelist)
        self.assertIn("images/2.png", output_zip_namelist)
        self.assertIn("images/3.png", output_zip_namelist)
        translations_txt = output_zip.read("translations.txt").decode("utf-8")
        self.assertIn("[1.png]", translations_txt)
        self.assertIn("[2.png]", translations_txt)
        self.assertIn("[3.png]", translations_txt)

    def test_output_project2(self):
        """测试导出项目全部内容（不含图片）"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            project.upload("1.png", file)
            project.upload("2.png", file)
            project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={"type": OutputTypes.ONLY_TEXT},
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_txt_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".txt"
        )
        translations_txt = output_txt_in_oss.read().decode("utf-8")
        self.assertIn("[1.png]", translations_txt)
        self.assertIn("[2.png]", translations_txt)
        self.assertIn("[3.png]", translations_txt)

    def test_output_project3(self):
        """测试导出项目部分内容 include（含图片）"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            file1 = project.upload("1.png", file)
            project.upload("2.png", file)
            file3 = project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={
                "type": OutputTypes.ALL,
                "file_ids_include": [str(file1.id), str(file3.id)],
            },
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_zip_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".zip"
        )
        output_zip = ZipFile(io.BytesIO(output_zip_in_oss.read()))
        output_zip_namelist = output_zip.namelist()
        # self.assertIn("ps_script.jsx", output_zip_namelist)
        self.assertIn("translations.txt", output_zip_namelist)
        self.assertIn("images/1.png", output_zip_namelist)
        self.assertNotIn("images/2.png", output_zip_namelist)
        self.assertIn("images/3.png", output_zip_namelist)
        translations_txt = output_zip.read("translations.txt").decode("utf-8")
        self.assertIn("[1.png]", translations_txt)
        self.assertNotIn("[2.png]", translations_txt)
        self.assertIn("[3.png]", translations_txt)

    def test_output_project4(self):
        """测试导出项目部分内容 include（不含图片）"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            file1 = project.upload("1.png", file)
            project.upload("2.png", file)
            file3 = project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={
                "type": OutputTypes.ONLY_TEXT,
                "file_ids_include": [str(file1.id), str(file3.id)],
            },
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_txt_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".txt"
        )
        translations_txt = output_txt_in_oss.read().decode("utf-8")
        self.assertIn("[1.png]", translations_txt)
        self.assertNotIn("[2.png]", translations_txt)
        self.assertIn("[3.png]", translations_txt)

    def test_output_project5(self):
        """测试导出项目部分内容 exclude（含图片）"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            file1 = project.upload("1.png", file)
            project.upload("2.png", file)
            file3 = project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={
                "type": OutputTypes.ALL,
                "file_ids_exclude": [str(file1.id), str(file3.id)],
            },
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_zip_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".zip"
        )
        output_zip = ZipFile(io.BytesIO(output_zip_in_oss.read()))
        output_zip_namelist = output_zip.namelist()
        # self.assertIn("ps_script.jsx", output_zip_namelist)
        self.assertIn("translations.txt", output_zip_namelist)
        self.assertNotIn("images/1.png", output_zip_namelist)
        self.assertIn("images/2.png", output_zip_namelist)
        self.assertNotIn("images/3.png", output_zip_namelist)
        translations_txt = output_zip.read("translations.txt").decode("utf-8")
        self.assertNotIn("[1.png]", translations_txt)
        self.assertIn("[2.png]", translations_txt)
        self.assertNotIn("[3.png]", translations_txt)

    def test_output_project6(self):
        """测试导出项目部分内容 exclude（不含图片）"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            file1 = project.upload("1.png", file)
            project.upload("2.png", file)
            file3 = project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={
                "type": OutputTypes.ONLY_TEXT,
                "file_ids_exclude": [str(file1.id), str(file3.id)],
            },
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_txt_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".txt"
        )
        translations_txt = output_txt_in_oss.read().decode("utf-8")
        self.assertNotIn("[1.png]", translations_txt)
        self.assertIn("[2.png]", translations_txt)
        self.assertNotIn("[3.png]", translations_txt)

    def test_output_project7(self):
        """测试导出项目时使用空数组仍然会导出全部"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        target = project.targets().first()
        token = self.get_creator(project).generate_token()
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
            project.upload("1.png", file)
            project.upload("2.png", file)
            project.upload("3.png", file)
        data = self.post(
            f"/v1/projects/{str(project.id)}/targets/{str(target.id)}/outputs",
            json={
                "type": OutputTypes.ALL,
                "file_ids_include": [],
                "file_ids_exclude": [],
            },
            token=token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(project.outputs().count(), 1)
        # 下载文件并查看是否正确
        output = project.outputs().first()
        output_zip_in_oss = oss.download(
            self.app.config["OSS_OUTPUT_PREFIX"], str(output.id) + ".zip"
        )
        output_zip = ZipFile(io.BytesIO(output_zip_in_oss.read()))
        output_zip_namelist = output_zip.namelist()
        # self.assertIn("ps_script.jsx", output_zip_namelist)
        self.assertIn("translations.txt", output_zip_namelist)
        self.assertIn("images/1.png", output_zip_namelist)
        self.assertIn("images/2.png", output_zip_namelist)
        self.assertIn("images/3.png", output_zip_namelist)
        translations_txt = output_zip.read("translations.txt").decode("utf-8")
        self.assertIn("[1.png]", translations_txt)
        self.assertIn("[2.png]", translations_txt)
        self.assertIn("[3.png]", translations_txt)
