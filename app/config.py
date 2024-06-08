# ===========
# 脱敏的生产环境配置（严禁记录密钥）
# 开发测试配置可放在 configs 文件夹下（已 gitignore）或项目外
# ===========
from os import environ as env

# -----------
# 基础设置
# -----------
SITE_NAME = env["SITE_NAME"]
SECRET_KEY = env["SECRET_KEY"]  # 必填 - 密钥
DEBUG = False
TESTING = False
MAX_CONTENT_LENGTH = int(env.get("MAX_CONTENT_LENGTH_MB", 1024)) * 1024 * 1024
ADMIN_EMAIL = env["ADMIN_EMAIL"]
# -----------
# Mongo 数据库
# -----------
DB_URI = f"mongodb://{env['MONGODB_USER']}:{env['MONGODB_PASS']}@moeflow-mongodb:27017/{env['MONGODB_DB_NAME']}?authSource=admin"
# -----------
# i18n
# -----------
BABEL_DEFAULT_LOCALE = "zh_Hans_CN"
BABEL_DEFAULT_TIMEZONE = "UTC"
# -----------
# 其他设置
# -----------
CONFIRM_EMAIL_WAIT_SECONDS = 60  # 重新发送确认邮箱邮件发送等待时间
RESET_EMAIL_WAIT_SECONDS = 60  # 重置邮箱验证码邮件发送等待时间
RESET_PASSWORD_WAIT_SECONDS = 60  # 重置密码邮件发送等待时间
PLAN_FINISH_DELTA = 7 * 24 * 60 * 60  # 计划完结延时时间
PLAN_DELETE_DELTA = 7 * 24 * 60 * 60  # 计划删除延时时间
OUTPUT_WAIT_SECONDS = 60 * 5  # 导出等待时间
# -----------
# 默认设置
# -----------
DEFAULT_USER_AVATAR = None
DEFAULT_TEAM_AVATAR = None
# -----------
# Storage 配置
# -----------
# 目前支持 LOCAL_STORAGE 和 OSS
STORAGE_TYPE = env["STORAGE_TYPE"]
# 未设置自定义域名则填写阿里云提供的 OSS 域名，格式如：https://<your-bucket-name>.<oss-region>.aliyuncs.com/
# 如果绑定了 CDN 来加速 OSS，则填写绑定在 CDN 的域名
# 本地储存填写绑定到服务器的域名，需用 nginx 指向 storage 文件夹，格式如：https://<your-domain>.com/storage/
STORAGE_DOMAIN = env["STORAGE_DOMAIN"]
OSS_ACCESS_KEY_ID = env.get("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = env.get("OSS_ACCESS_KEY_SECRET", "")
OSS_ENDPOINT = env.get("OSS_ENDPOINT", "")
OSS_BUCKET_NAME = env.get("OSS_BUCKET_NAME", "")
OSS_PROCESS_COVER_NAME = env.get("OSS_PROCESS_COVER_NAME", "cover")
OSS_PROCESS_SAFE_CHECK_NAME = env.get("OSS_PROCESS_SAFE_CHECK_NAME", "safe-check")
# 如果 OSS 绑定了 CDN 来加速，同时开启了 CDN 的 [阿里云 OSS 私有 Bucket 回源] 和 [URL 鉴权]，
# 此时需要设置 STORAGE_DOMAIN 为 CDN 域名，且设置 OSS_VIA_CDN = True，
# 这样程序将通过 CDN 的 URL 鉴权方式来生成 CDN URL，而不用 OSS 的 URL 签名鉴权
OSS_VIA_CDN = True if env.get("OSS_VIA_CDN", "") == "True" else False
# CDN URL 鉴权主/备 KEY
CDN_URL_KEY_A = env.get("CDN_URL_KEY_A", "")
CDN_URL_KEY_B = env.get("CDN_URL_KEY_B", "")  # 备 KEY 暂未用到
# -----------
# 内容安全
# -----------
SAFE_ACCESS_KEY_ID = "-"
SAFE_ACCESS_KEY_SECRET = "-"
# -----------
# 各类储存前缀
# -----------
OSS_FILE_PREFIX = "files/"
OSS_OUTPUT_PREFIX = "outputs/"
OSS_USER_AVATAR_PREFIX = "user-avatars/"
OSS_TEAM_AVATAR_PREFIX = "team-avatars/"
# -----------
# 谷歌接口
# -----------
GOOGLE_HTTP_PROXY = None
GOOGLE_REVERSE_PROXY_AUTH = (
    env.get("GOOGLE_REVERSE_PROXY_USER", ""),
    env.get("GOOGLE_REVERSE_PROXY_PASS", ""),
)
# -----------
# 谷歌 OCR(Vision) 接口
# -----------
GOOGLE_OCR_API_KEY = env.get("GOOGLE_OCR_API_KEY", "")
GOOGLE_OCR_API_URL = (
    "https://vision.googleapis.com/v1/images:annotate" + f"?key={GOOGLE_OCR_API_KEY}"
)
# -----------
# 谷歌云储存（用于中转 OCR(Vision) 接口所使用的 bucket）
# -----------
GOOGLE_STORAGE_MOEFLOW_VISION_TMP = {
    "JSON": env.get("GOOGLE_STORAGE_JSON_PATH", ""),
    "BUCKET_NAME": env.get("GOOGLE_STORAGE_BUCKET_NAME", ""),
    "GS_URL": "gs://" + env.get("GOOGLE_STORAGE_GS_URL", ""),
}
# -----------
# EMAIL SMTP
# -----------
ENABLE_USER_EMAIL = (
    True if env["ENABLE_USER_EMAIL"] == "True" else False
)  # 发送用户邮件（验证码等）
ENABLE_LOG_EMAIL = True if env["ENABLE_LOG_EMAIL"] == "True" else False  # 发送日志邮件
EMAIL_SMTP_HOST = env.get("EMAIL_SMTP_HOST", "")  # SMTP服务器地址
EMAIL_SMTP_PORT = env.get("EMAIL_SMTP_PORT", 465)  # SMTP服务器端口
EMAIL_USE_SSL = True if env.get("EMAIL_USE_SSL", "") == "True" else False
EMAIL_ADDRESS = env.get("EMAIL_ADDRESS", "")
EMAIL_USERNAME = env.get("EMAIL_USERNAME", "")  # SMTP服务器用户名，通常是邮箱全称
EMAIL_PASSWORD = env.get("EMAIL_PASSWORD", "")  # SMTP服务器密码
EMAIL_REPLY_ADDRESS = env.get("EMAIL_ADDRESS", "")
EMAIL_ERROR_ADDRESS = env.get("EMAIL_ADDRESS", "")
# -----------
# Celery
# -----------
CELERY_BROKER_URL = env.get(
    "CELERY_BROKER_URL",
    f"amqp://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASS']}@moeflow-rabbitmq:5672/{env['RABBITMQ_VHOST_NAME']}",
)
CELERY_BACKEND_URL = env.get("CELERY_BACKEND_URL", DB_URI)
CELERY_MONGODB_BACKEND_SETTINGS = {
    "database": env["MONGODB_DB_NAME"],
    "taskmeta_collection": "celery_taskmeta",
}
# -----------
# APIKit
# -----------
APIKIT_PAGINATION_PAGE_KEY = "page"
APIKIT_PAGINATION_LIMIT_KEY = "limit"
APIKIT_PAGINATION_DEFAULT_LIMIT = 30  # 每页条目数
APIKIT_PAGINATION_MAX_LIMIT = 100
APIKIT_ACCESS_CONTROL_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Requested-With",
]
# manga-image-translator worker
MIT_STORAGE_ROOT = env.get("MIT_STORAGE_ROOT", None)
