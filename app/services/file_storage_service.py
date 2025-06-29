"""
文件存储服务 (基本用于图片)

- 读写文件 (本地或云)
- 为文件生成供客户端使用的URL

代替1.0.7之前的oss+本地存储
"""

from __future__ import annotations

import asyncio
import io
import werkzeug
import opendal
import mimetypes
from typing import Union, Optional, List

from app.constants.storage import StorageType, OpendalStorageService
from asgiref.sync import async_to_sync
from app.utils.logging import logger
from .file_storage_abstract import AbstractStorageService


def create_opendal_storage_service(config: dict[str, str]) -> OpenDalStorageService:
    if config['STORAGE_TYPE'] != StorageType.OPENDAL:
        raise Exception("unexpected STORAGE_TYPE")

    if config.get('OPENDAL_SERVICE') == OpendalStorageService.GCS:
        url_builder = GcpUrlBuilder(config)

        operator = opendal.AsyncOperator("gcs",
                                         bucket=config['OPENDAL_GCS_BUCKET'],
                                         root="/")
        return OpenDalStorageService(url_builder, operator)

    raise Exception("unsupported STORAGE_PROVIDER: {0}".format(config.get('OPENDAL_SERVICE')))


def read_key_file(path_or_value: str) -> str:
    with open(path_or_value, "r") as f:
        return f.read()


class OpenDalStorageService(AbstractStorageService):
    """
    各种云存储服务的io
    """

    def __init__(self, url_builder: GcpUrlBuilder, operator: opendal.AsyncOperator):
        self.url_builder = url_builder
        self.operator = operator

    def upload(self, path: str, filename: str,
               file: io.BufferedReader | werkzeug.wrappers.request.FileStorage | str,
               headers: Optional[dict[str, int | str]] = None, progress_callback=None) -> None:
        self._sync_upload(path, filename, file, headers or {})

    @async_to_sync
    async def _sync_upload(self, path: str, filename: str,
                           file: io.BufferedReader | werkzeug.wrappers.request.FileStorage | str,
                           headers: dict[str, int | str]):
        blob: bytes = file.encode() if isinstance(file, str) else file.read()

        aliased_headers = {
            'content_type': 'Content-Type',
            'cache_control': 'Cache-Control',
            'content_disposition': 'Content-Disposition',
        }
        write_kwargs = {
            k1: headers.get(k1) or headers.get(k2)
            for (k1, k2) in aliased_headers.items()
            if (k1 in headers) or (k2 in headers)
        }
        if "content_type" not in write_kwargs:
            guessed_type, guessed_encoding = mimetypes.guess_type(filename)
            if guessed_type:
                write_kwargs['content_type'] = guessed_type
        if "cache_control" not in write_kwargs:
            write_kwargs["cache_control"] = "private, max-age=31536000, must-revalidate"
        await self.operator.write(path + filename, blob, **write_kwargs)

    def download(self, path: str, filename: str, /, *, local_path=None) -> Optional[io.BytesIO]:
        """下载文件"""
        if local_path:
            self._download_to_file(path, filename, local_path)
        else:
            downloaded: memoryview = self._download_to_memory(path, filename)
            return io.BytesIO(downloaded)

    @async_to_sync
    async def _download_to_memory(self, path: str, filename: str):
        return await self.operator.read("{0}/{1}".format(path, filename))

    @async_to_sync
    async def _download_to_file(self, path: str, filename: str, local_path: str):
        blob = await self.operator.read("{0}/{1}".format(path, filename))
        with open(local_path, "wb") as f:
            f.write(bytes(blob))

    def is_exist(self, path, filename, process_name=None) -> bool:
        """检查文件是否存在"""
        return self._is_exist(path, filename)

    @async_to_sync
    async def _is_exist(self, path, filename):
        metadata = await self.operator.stat(path + filename)
        # FIXME
        return True

    def delete(self, path_prefix: str, filename: List[str] | str):
        self._sync_delete(path_prefix, filename)

    @async_to_sync
    async def _sync_delete(self, path_prefix: str, filename: List[str] | str):
        targets = filename if isinstance(filename, list) else [filename]
        await asyncio.gather(
            *[self.operator.delete(path_prefix + t) for t in targets]
        )

    def sign_url(self, path_prefix: str, filename: str, expires: int = 3600, process_name: str = None) -> str:
        """生成URL"""
        return self.url_builder.create_public_url(path_prefix, filename, expires=expires, process_name=process_name)


class GcpUrlBuilder:
    """
    GCP Cloud Storage的URL生成
    """

    def __init__(self, options: dict[str, str]):
        self.bucket_name = options['OPENDAL_GCS_BUCKET']

    def create_public_url(self, path_prefix: str, filename: str, /, **kwargs) -> str:
        return f"https://storage.cloud.google.com/{self.bucket_name}/{path_prefix}{filename}"
