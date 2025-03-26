"""
对接阿里云OSS储存服务
"""
import io
from io import BufferedReader, BytesIO, FileIO
import os
import re
import shutil
import time
import hashlib
import logging
from typing import Union
from urllib import parse
from typing import List, Union, Optional

import werkzeug
import oss2
from oss2 import to_string
from oss2.exceptions import NoSuchKey

from app.constants.storage import StorageType
from .file_storage_service import create_opendal_storage_service, OpenDalStorageService
from .file_storage_abstract import AbstractStorageService

logger = logging.getLogger(__name__)


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


class OSS(AbstractStorageService):
    def __init__(self, config=None):
        # exists for all storage types
        self.storage_type = None
        self.oss_domain: Optional[None] = None  # URL prefix for (asset URL for clients)
        # only exists for OSS
        self.auth: Optional[oss2.Auth] = None
        self.bucket: Optional[oss2.Bucket] = None
        self.oss_via_cdn: Optional[str] = None
        self.cdn_url_key: Optional[str] = None
        # only exists for local storage
        self.local_storage_path: Optional[str] = None
        # only exists for OpenDal storage
        self.delegated_impl: Optional[OpenDalStorageService] = None
        if config:
            self.init(config)

    def init(self, config: dict[str, str]):
        """配置初始化"""
        if self.storage_type:
            raise Exception("already initialized")
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
        elif self.storage_type == StorageType.LOCAL_STORAGE:
            from app import STORAGE_PATH
            self.oss_domain = config["STORAGE_DOMAIN"]
            self.local_storage_path = STORAGE_PATH
        elif self.storage_type == StorageType.OPENDAL:
            self.delegated_impl = create_opendal_storage_service(config)
        else:
            raise NotImplemented('unsupported STORAGE_TYPE: {0}'.format(self.storage_type))

    def upload(
        self,
        path: str,
        filename: str,
        file: Union[str, io.BufferedReader, FileIO , werkzeug.wrappers.request.FileStorage ],
        headers=None,
        progress_callback=None,
    ) -> None:
        """上传文件"""
        if self.storage_type == StorageType.OSS:
            return self.bucket.put_object(
                path + filename,
                file,
                headers=headers,
                progress_callback=progress_callback,
            )
        elif self.storage_type == StorageType.LOCAL_STORAGE:
            folder_path = os.path.join(self.local_storage_path, path)
            os.makedirs(folder_path, exist_ok=True)
            if isinstance(file, io.BufferedReader):
                with open(os.path.join(folder_path, filename), "wb") as saved_file:
                    saved_file.write(file.read())
            elif isinstance(file, str):
                with open(os.path.join(folder_path, filename), "w") as saved_file:
                    saved_file.write(file)
            elif isinstance(file, werkzeug.wrappers.request.FileStorage):
                file.save(os.path.join(folder_path, filename))
            logging.debug("saved file : %s / %s", folder_path, filename)
        elif self.storage_type == StorageType.OPENDAL:
            self.delegated_impl.upload(path, filename, file, headers, progress_callback)
        else:
            raise Exception("unsupported STORAGE_TYPE")

    def download(self, path: str, filename: str, /, *, local_path: Optional[str] = None) -> Optional[io.BytesIO]:
        """下载文件"""
        # 如果提供local_path，则下载到本地
        if self.storage_type == StorageType.OSS:
            if local_path:
                self.bucket.get_object_to_file(path + filename, local_path)
            else:
                return self.bucket.get_object(path + filename)
        elif self.storage_type == StorageType.LOCAL_STORAGE:
            folder_path = os.path.join(self.local_storage_path, path)
            file_path = os.path.join(folder_path, filename)
            if local_path:
                if self.is_exist(folder_path, filename):
                    shutil.copy2(file_path, local_path)
                else:
                    raise NoSuchKey(status=404, headers={}, body={}, details={})
            else:
                with open(file_path, "rb") as file:
                    return io.BytesIO(file.read())
        elif self.storage_type == StorageType.OPENDAL:
            return self.delegated_impl.download(path, filename, local_path=local_path)
        else:
            raise Exception("unsupported STORAGE_TYPE")

    def is_exist(self, path: str, filename: str, process_name: Optional[str] = None) -> bool:
        """检查文件是否存在"""
        if self.storage_type == StorageType.OSS:
            return self.bucket.object_exists(path + filename)
        elif self.storage_type == StorageType.LOCAL_STORAGE:
            if os.path.isabs(path):
                return os.path.isfile(
                    os.path.join(
                        path,
                        (process_name + "-" if process_name is not None else "")
                        + filename,
                    )
                )
            else:
                return os.path.isfile(
                    os.path.join(
                        self.local_storage_path,
                        path,
                        (process_name + "-" if process_name is not None else "")
                        + filename,
                    )
                )
        elif self.storage_type == StorageType.OPENDAL:
            return self.delegated_impl.is_exist(path, filename, process_name)
        else:
            raise Exception("unsupported STORAGE_TYPE")

    def delete(self, path: str, filename: Union[List[str], str]):
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
        elif self.storage_type == StorageType.LOCAL_STORAGE:
            folder_path = os.path.join(self.local_storage_path, path)
            # 如果给予列表，则批量删除
            if isinstance(filename, list):
                for name in filename:
                    if self.is_exist(folder_path, name):
                        os.remove(os.path.join(folder_path, name))
            else:
                if self.is_exist(folder_path, filename):
                    os.remove(os.path.join(folder_path, filename))
        elif self.storage_type == StorageType.OPENDAL:
            self.delegated_impl.delete(path, filename)
        else:
            raise Exception("unsupported STORAGE_TYPE")

    def rmdir(self, path: Union[str, List[str]]):
        """（批量）删除文件夹，仅本地储存"""
        if self.storage_type == StorageType.LOCAL_STORAGE:
            # 如果给予列表，则批量删除
            if isinstance(path, list):
                for p in path:
                    folder_path = os.path.join(self.local_storage_path, p)
                    if os.path.isdir(folder_path) and len(os.listdir(folder_path)) == 0:
                        os.rmdir(folder_path)
            else:
                folder_path = os.path.join(self.local_storage_path, path)
                if os.path.isdir(folder_path) and len(os.listdir(folder_path)) == 0:
                    os.rmdir(folder_path)

    def sign_url(self, *args, **kwargs):
        if self.storage_type == StorageType.OSS:
            if self.oss_via_cdn:
                return self._sign_cdn_url(*args, **kwargs)
            else:
                return self._sign_oss_url(*args, **kwargs)
        elif self.storage_type == StorageType.LOCAL_STORAGE:
            return self._sign_local_url(*args, **kwargs)
        elif self.storage_type == StorageType.OPENDAL:
            return self.delegated_impl.sign_url(*args, **kwargs)
        else:
            raise Exception("unsupported STORAGE_TYPE")

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
        uri = oss_domain + path + parse.quote(filename)
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
            method, oss_domain + parse.quote(key), headers=headers, params=params
        )
        return self.bucket.auth._sign_url(req, self.bucket.bucket_name, key, expires)
