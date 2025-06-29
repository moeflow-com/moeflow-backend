from app.constants.base import StrType


class StorageType(StrType):
    OSS = "OSS"
    LOCAL_STORAGE = "LOCAL_STORAGE"
    OPENDAL = "OPENDAL"


class OpendalStorageService(StrType):
    GCS = "GCS"  # Google Cloud Storage
