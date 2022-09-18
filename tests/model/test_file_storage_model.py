import os

import requests
from bson import ObjectId

from app import TMP_PATH, oss
from tests import MoeTestCase


class OSSModelTestCase(MoeTestCase):
    path = "test/"

    def test_upload_and_delete(self):
        """测试上传删除"""
        filename = str(ObjectId()) + ".txt"
        self.assertFalse(oss.is_exist(self.path, filename))
        oss.upload(self.path, filename, "1")
        self.assertTrue(oss.is_exist(self.path, filename))
        # 清理，删除上传的内容
        oss.delete(self.path, filename)
        self.assertFalse(oss.is_exist(self.path, filename))

    def test_delete(self):
        """测试删除和批量删除"""
        # 上传三个文件
        filename1 = str(ObjectId()) + ".txt"
        filename2 = str(ObjectId()) + ".txt"
        filename3 = str(ObjectId()) + ".txt"
        self.assertFalse(oss.is_exist(self.path, filename1))
        self.assertFalse(oss.is_exist(self.path, filename2))
        self.assertFalse(oss.is_exist(self.path, filename3))
        oss.upload(self.path, filename1, "1")
        oss.upload(self.path, filename2, "2")
        oss.upload(self.path, filename3, "3")
        self.assertTrue(oss.is_exist(self.path, filename1))
        self.assertTrue(oss.is_exist(self.path, filename2))
        self.assertTrue(oss.is_exist(self.path, filename3))
        # 删除第一个
        oss.delete(self.path, filename1)
        self.assertFalse(oss.is_exist(self.path, filename1))
        # 批量删除后两个
        oss.delete(self.path, [filename2, filename3])
        self.assertFalse(oss.is_exist(self.path, filename2))
        self.assertFalse(oss.is_exist(self.path, filename3))

    def test_download(self):
        """测试下载"""
        # 上传两个文件
        filename1 = str(ObjectId()) + ".txt"
        filename2 = str(ObjectId()) + ".txt"
        self.assertFalse(oss.is_exist(self.path, filename1))
        self.assertFalse(oss.is_exist(self.path, filename2))
        oss.upload(self.path, filename1, filename1)
        oss.upload(self.path, filename2, filename2)
        self.assertTrue(oss.is_exist(self.path, filename1))
        self.assertTrue(oss.is_exist(self.path, filename2))
        # 下载第一个为对象
        file1 = oss.download(self.path, filename1)
        self.assertEqual(filename1.encode("utf-8"), file1.read())
        # 下载第二个为文件
        file2_path = os.path.join(TMP_PATH, filename2)
        oss.download(self.path, filename2, local_path=file2_path)
        with open(file2_path) as file2:
            self.assertEqual(filename2, file2.read())
        # 清理，删除这两个文件
        os.remove(file2_path)  # 删除本地文件
        oss.delete(self.path, [filename1, filename2])
        self.assertFalse(oss.is_exist(self.path, filename1))
        self.assertFalse(oss.is_exist(self.path, filename2))

    def test_sign_url(self):
        """测试签发url"""
        # 上传个文件
        filename1 = str(ObjectId()) + ".jpg"
        self.assertFalse(oss.is_exist(self.path, filename1))
        oss.upload(self.path, filename1, filename1)
        self.assertTrue(oss.is_exist(self.path, filename1))
        # 直接用链接访问，报错
        response = requests.get(self.app.config["OSS_DOMAIN"] + self.path + filename1)
        self.assertEqual(403, response.status_code)
        # 签名后的url可以访问
        url = oss.sign_url(self.path, filename1)
        response = requests.get(url)
        self.assertEqual(filename1, response.text)
        # 清理，删除这个文件
        oss.delete(self.path, [filename1])
        self.assertFalse(oss.is_exist(self.path, filename1))
