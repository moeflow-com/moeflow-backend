import os


def get_file_size(file, unit="kb"):
    """获取文件大小，默认返回kb为单位的数值"""
    file.seek(0, os.SEEK_END)  # 移动到文件尾部
    size = file.tell()  # 获取文件大小，单位是Byte
    file.seek(0)  # 将指针移回开头
    if unit.lower() == "kb":
        size = size / 1024
    elif unit.lower() == "mb":
        size = size / 1024 / 1024
    elif unit.lower() == "gb":
        size = size / 1024 / 1024 / 1024
    elif unit.lower() == "tb":
        size = size / 1024 / 1024 / 1024 / 1024
    elif unit.lower() == "bit":
        size = size * 8
    return size
