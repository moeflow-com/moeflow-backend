from abc import ABC, abstractmethod
import io

import werkzeug
from typing import Union, List, Optional


class FSSException(Exception):
    pass


class FSSKeyNotFound(FSSException):
    pass


class AbstractStorageService(ABC):
    @abstractmethod
    def upload(self, path: str, filename: str,
               file: io.BufferedReader | werkzeug.wrappers.request.FileStorage | str,
               headers: Optional[dict[str, int | str]] = None, progress_callback=None):
        """上传文件"""
        pass

    @abstractmethod
    def download(self, path: str, filename: str, /, *, local_path=None) -> Optional[io.BytesIO]:
        """下载文件"""
        pass

    @abstractmethod
    def is_exist(self, path: str, filename: str, process_name: Optional[str] = None) -> bool:
        """检查文件是否存在"""
        pass

    @abstractmethod
    def delete(self, path: str, filename: Union[List[str], str]):
        pass

    @abstractmethod
    def sign_url(self, *args, **kwargs) -> str:
        pass
