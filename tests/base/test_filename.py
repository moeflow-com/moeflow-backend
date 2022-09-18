from app.exceptions import FilenameIllegalError
from app.models.file import Filename
from tests import MoeTestCase


class FilenameTestCase(MoeTestCase):
    """测试util中Filename类"""

    def test_check_vaild_filename(self):
        with self.app.test_request_context():
            self.assertIsNotNone(Filename("hi"))
            self.assertIsNotNone(Filename(" hi"))
            self.assertIsNotNone(Filename("hi.txt"))
            self.assertIsNotNone(Filename(" hi.txt"))
            self.assertIsNotNone(Filename("1.hi.txt"))
            with self.assertRaises(FilenameIllegalError):
                Filename("")
            with self.assertRaises(FilenameIllegalError):
                Filename("/.txt")
            with self.assertRaises(FilenameIllegalError):
                Filename("\.txt")  # noqa: W605
            with self.assertRaises(FilenameIllegalError):
                Filename("?.txt")
            with self.assertRaises(FilenameIllegalError):
                Filename("<.txt")
            with self.assertRaises(FilenameIllegalError):
                Filename(">.txt")
            with self.assertRaises(FilenameIllegalError):
                Filename(":.txt")
            with self.assertRaises(FilenameIllegalError):
                Filename("*.txt")
            with self.assertRaises(FilenameIllegalError):
                Filename(".txt")
            with self.assertRaises(FilenameIllegalError):
                Filename(" .txt")
            with self.assertRaises(FilenameIllegalError):
                Filename(".")
            with self.assertRaises(FilenameIllegalError):
                Filename("..")
            with self.assertRaises(FilenameIllegalError):
                Filename(" . ")
            with self.assertRaises(FilenameIllegalError):
                Filename(" .. ")
            with self.assertRaises(FilenameIllegalError):
                Filename(" . . ")
            with self.assertRaises(FilenameIllegalError):
                Filename(" ..")
            with self.assertRaises(FilenameIllegalError):
                Filename(".. ")
            with self.assertRaises(FilenameIllegalError):
                Filename(" . .")
            with self.assertRaises(FilenameIllegalError):
                Filename(". . ")
            with self.assertRaises(FilenameIllegalError):
                Filename("hi.")
            with self.assertRaises(FilenameIllegalError):
                Filename("hi. ")

    def test_filename(self):
        with self.app.test_request_context():
            # 获取前缀
            self.assertEqual(Filename("hi.txt").prefix, "hi")
            self.assertEqual(Filename(" hi.txt").prefix, " hi")
            self.assertEqual(Filename("hi .txt").prefix, "hi ")
            self.assertEqual(Filename("hi.there.txt").prefix, "hi.there")
            # 获取后缀
            self.assertEqual(Filename("hi").suffix, "")
            self.assertEqual(Filename("hi.txt").suffix, "txt")
            self.assertEqual(Filename("hi.there.txt").suffix, "txt")
            self.assertEqual(Filename("hi. txt").suffix, " txt")
            self.assertEqual(Filename("hi.txt ").suffix, "txt ")
            # 获取后缀
            self.assertEqual(Filename("hi").suffix, "")
            self.assertEqual(Filename("hi.txt").suffix, "txt")
            self.assertEqual(Filename("hi.there.txt").suffix, "txt")
            self.assertEqual(Filename("hi. txt").suffix, " txt")
            self.assertEqual(Filename("hi.txt ").suffix, "txt ")
            # 获取排序名
            self.assertEqual("a", Filename("a").sort_name)
            self.assertEqual("a", Filename("a.md").sort_name)
            self.assertEqual("000001", Filename("1").sort_name)
            self.assertEqual("000001", Filename("1.safsad").sort_name)
            self.assertEqual("000002", Filename("2").sort_name)
            self.assertEqual("000010", Filename("10").sort_name)
            self.assertEqual("099999", Filename("99999").sort_name)
            self.assertEqual("999999", Filename("999999").sort_name)
            self.assertEqual("9999999", Filename("9999999").sort_name)
            self.assertEqual("a000001", Filename("a1").sort_name)
            self.assertEqual("000001a", Filename("1a").sort_name)
            self.assertEqual("a000001a", Filename("a1a").sort_name)
            self.assertEqual("000001a000001", Filename("1a1").sort_name)
            self.assertEqual(
                "book000001-000012--1200001 (000001) ",
                Filename("book1-12--1200001 (1) .jpg").sort_name,
            )
            self.assertEqual(
                "000059bbf000003e000008bced000008f000001afd000052b",
                Filename("59bbf3e8bced8f0001afd52b").sort_name,
            )
