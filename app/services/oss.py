"""
对接阿里云OSS储存服务
"""
from io import BufferedReader, BytesIO
import os
import re
import shutil
import time
import hashlib

import oss2
from oss2 import to_string
from oss2.exceptions import NoSuchKey

from app.constants.storage import StorageType


def md5sum(src):
    m = hashlib.md5()
    m.update(src)
    return m.hexdigest()


def aliyun_cdn_url_auth_c(uri, key, exp):
    """阿里云 CDN 鉴权方式 C"""
    p = re.compile("^(http://|https://)?([^/?]+)(/[^?]*)?(\\?.*)?$")
    if not p:
        return None
    m = p.match(uri)
    scheme, host, path, args = m.groups()
    if not scheme:
        scheme = "http://"
    if not path:
        path = "/"
    if not args:
        args = ""
    hexexp = "%x" % exp
    sstring = key + path + hexexp
    hashvalue = md5sum(sstring.encode("utf-8"))
    return "%s%s/%s/%s%s%s" % (scheme, host, hashvalue, hexexp, path, args)


class OSS:
    def __init__(self, config=None):
        if config:
            self.init(config)
        else:
            self.storage_type = None
            self.auth = None
            self.bucket = None
            self.oss_domain = None
            self.oss_via_cdn = None
            self.cdn_url_key = None

    def init(self, config):
        """配置初始化"""
        self.storage_type = config["STORAGE_TYPE"]
        if self.storage_type == StorageType.OSS:
            self.auth = oss2.Auth(
                config["OSS_ACCESS_KEY_ID"],
                config["OSS_ACCESS_KEY_SECRET"],
            )
            self.bucket = oss2.Bucket(
                self.auth,
                config["OSS_ENDPOINT"],
                config["OSS_BUCKET_NAME"],
            )

            self.oss_domain = config["STORAGE_DOMAIN"]
            self.oss_via_cdn = config["OSS_VIA_CDN"]
            self.cdn_url_key = config["CDN_URL_KEY_A"]
        else:
            from app import STORAGE_PATH

            self.oss_domain = config["STORAGE_DOMAIN"]
            self.STORAGE_PATH = STORAGE_PATH

    def upload(self, path, filename, file, headers=None, progress_callback=None):
        """上传文件"""
        print("path: ", path)
        print("filename: ", filename)
        if self.storage_type == StorageType.OSS:
            return self.bucket.put_object(
                path + filename,
                file,
                headers=headers,
                progress_callback=progress_callback,
            )
        else:
            folder_path = os.path.join(self.STORAGE_PATH, path)
            os.makedirs(folder_path, exist_ok=True)
            if isinstance(file, BufferedReader):
                with open(os.path.join(folder_path, filename), "wb") as saved_file:
                    saved_file.write(file.read())
            elif isinstance(file, str):
                with open(os.path.join(folder_path, filename), "w") as saved_file:
                    saved_file.write(file)
            else:
                file.save(os.path.join(folder_path, filename))

    def download(self, path, filename, /, *, local_path=None):
        """下载文件"""
        # 如果提供local_path，则下载到本地
        if self.storage_type == StorageType.OSS:
            if local_path:
                self.bucket.get_object_to_file(path + filename, local_path)
            else:
                return self.bucket.get_object(path + filename)
        else:
            folder_path = os.path.join(self.STORAGE_PATH, path)
            file_path = os.path.join(folder_path, filename)
            if local_path:
                if self.is_exist(folder_path, filename):
                    shutil.copy2(file_path, local_path)
                else:
                    raise NoSuchKey(status=404, headers={}, body={}, details={})
            else:
                with open(file_path, "rb") as file:
                    return BytesIO(file.read())

    def is_exist(self, path, filename):
        """检查文件是否存在"""
        if self.storage_type == StorageType.OSS:
            return self.bucket.object_exists(path + filename)
        else:
            if os.path.isabs(path):
                return os.path.isfile(os.path.join(path, filename))
            else:
                return os.path.isfile(os.path.join(self.STORAGE_PATH, path, filename))

    def delete(self, path, filename):
        """（批量）删除文件"""
        if self.storage_type == StorageType.OSS:
            # 如果给予列表，则批量删除
            if isinstance(filename, list):
                if len(filename) == 0:
                    return
                result = self.bucket.batch_delete_objects(
                    [path + name for name in filename]
                )
            else:
                result = self.bucket.delete_object(path + filename)
            return result
        else:
            folder_path = os.path.join(self.STORAGE_PATH, path)
            # 如果给予列表，则批量删除
            if isinstance(filename, list):
                for name in filename:
                    if self.is_exist(folder_path, name):
                        os.remove(os.path.join(folder_path, name))
            else:
                if self.is_exist(folder_path, filename):
                    os.remove(os.path.join(folder_path, filename))

    def sign_url(self, *args, **kwargs):
        if self.storage_type == StorageType.OSS:
            if self.oss_via_cdn:
                return self._sign_cdn_url(*args, **kwargs)
            else:
                return self._sign_oss_url(*args, **kwargs)
        else:
            return self._sign_local_url(*args, **kwargs)

    def _sign_local_url(
        self,
        path,
        filename,
        expires=604800,
        oss_domain=None,
        process_name=None,
        **kwargs,
    ):
        return (
            self.oss_domain
            + path
            + (process_name + "-" if process_name is not None else "")
            + filename
        )

    def _sign_cdn_url(
        self,
        path,
        filename,
        expires=604800,
        oss_domain=None,
        process_name=None,
        **kwargs,
    ):
        """
        通过 CDN 的 URL 鉴权生成可以访问的 URL，此时 oss_domain 需要是绑定于 CDN 的域名
        """
        # 验证失效时间为1-8天，缓存失效时间为0-7天
        # 过期时间对齐到下一个expires，以使用http缓存，过期时间最长为设置的时间的两倍
        now = int(time.time())
        delta = expires - now % expires
        expires = delta + 86400  # 失效时间加一天，以免获取到url，下一秒就失效了
        # 如果没有指定oss_domain，则使用配置中的STORAGE_DOMAIN
        if oss_domain is None:
            oss_domain = self.oss_domain
        uri = oss_domain + path + filename
        url = aliyun_cdn_url_auth_c(uri=uri, key=self.cdn_url_key, exp=now + expires)
        if process_name:
            url += f"?x-oss-process=style/{process_name}"
        return url

    def _sign_oss_url(
        self,
        path,
        filename,
        expires=604800,
        headers=None,
        params=None,
        method="GET",
        oss_domain=None,
        download=False,
        process_name=None,
    ):
        """
        通过 OSS 的 URL 签名生成可以访问的 URL，默认使用配置中用户自定义的 OSS 域名
        """
        # 验证失效时间为1-8天，缓存失效时间为0-7天
        # 过期时间对齐到下一个expires，以使用http缓存，过期时间最长为设置的时间的两倍
        delta = expires - int(time.time()) % expires
        expires = delta + 86400  # 失效时间加一天，以免获取到url，下一秒就失效了
        # 如果没有指定oss_domain，则使用配置中的STORAGE_DOMAIN
        if oss_domain is None:
            oss_domain = self.oss_domain
        if params is None:
            params = {}
        if download:
            params["response-content-disposition"] = "attachment"
        if process_name:
            params["x-oss-process"] = f"style/{process_name}"
        key = to_string(path + filename)
        req = oss2.http.Request(
            method, oss_domain + key, headers=headers, params=params
        )
        return self.bucket.auth._sign_url(req, self.bucket.bucket_name, key, expires)
