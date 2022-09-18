from google.cloud import storage


class GoogleStorage:
    def __init__(self, config=None):
        if config:
            self.init(config)
        else:
            self.client = None
            self.bucket = None

    def init(self, config):
        """配置初始化"""
        self.client = storage.Client.from_service_account_json(
            config["GOOGLE_STORAGE_MOEFLOW_VISION_TMP"]["JSON"]
        )
        self.bucket = self.client.bucket(
            config["GOOGLE_STORAGE_MOEFLOW_VISION_TMP"]["BUCKET_NAME"]
        )

    def upload_from_string(self, path, filename, file):
        """上传文件"""
        blob = self.bucket.blob(path + filename)
        blob.upload_from_string(file)
        return blob

    def upload(self, path, filename, file):
        """上传文件"""
        blob = self.bucket.blob(path + filename)
        blob.upload_from_file(file)
        return blob
