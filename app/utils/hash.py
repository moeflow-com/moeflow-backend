import hashlib
from io import BufferedReader


def md5(src):
    """获取字符串的md5"""
    m = hashlib.md5()
    m.update(src.encode("UTF-8"))
    return m.hexdigest()


def get_file_md5(file):
    """获取文件的md5"""
    m = hashlib.md5()
    m.update(file.read())
    # 如果是文件，则还原指针
    if isinstance(file, BufferedReader):
        file.seek(0)
    return m.hexdigest()
