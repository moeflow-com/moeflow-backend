# ===========
# 脱敏的生产环境配置（严禁记录密钥）
# 开发测试配置可放在 configs 文件夹下（已 gitignore）或项目外
# ===========
from os import environ as env

# -----------
# 基础设置
# -----------
APP_NAME = "moeflow"
SECRET_KEY = env["SECRET_KEY"]
DEBUG = False
TESTING = False
MAX_CONTENT_LENGTH = 20 * 1024 * 1024
# -----------
# Mongo 数据库
# -----------
DB_URI = (
    f"mongodb://{env['MONGO_USER']}:{env['MONGO_PASS']}"
    + f"@mongo:27017/{APP_NAME}?authSource=admin"
)
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
# -----------
# 默认设置
# -----------
DEFAULT_USER_AVATAR = None
DEFAULT_TEAM_AVATAR = None
# -----------
# OSS
# -----------
OSS_ACCESS_KEY_ID = env["OSS_ACCESS_KEY_ID"]
OSS_ACCESS_KEY_SECRET = env["OSS_ACCESS_KEY_SECRET"]
OSS_ENDPOINT = "https://oss-cn-shanghai-internal.aliyuncs.com/"  # 线上需要修改成内网端点
OSS_BUCKET_NAME = "moeflow"
# OSS_DOMAIN 可能绑定在 CDN 来加速 OSS，并开启了 CDN 的[阿里云 OSS 私有 Bucket 回源]和[URL 鉴权]，
# 此时需要设置 OSS_VIA_CDN = True，将通过 CDN 的 URL 鉴权方式来生成 URL，而不用 OSS 的 URL 签名
OSS_VIA_CDN = False
# CDN URL 鉴权主/备 KEY
CDN_URL_KEY_A = env["CDN_URL_KEY_A"]
CDN_URL_KEY_B = env["CDN_URL_KEY_B"]  # 备 KEY 暂未用到
# 用户自定义域名（未设置则填写阿里云提供的 OSS 域名）
OSS_DOMAIN = "https://data.moeflow.com/"
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
    env["GOOGLE_REVERSE_PROXY_USER"],
    env["GOOGLE_REVERSE_PROXY_PASS"],
)
# -----------
# 谷歌 OCR(Vision) 接口
# -----------
GOOGLE_OCR_API_KEY = env["GOOGLE_OCR_API_KEY"]
GOOGLE_OCR_API_URL = (
    "https://vision.googleapis.com/v1/images:annotate" + f"?key={GOOGLE_OCR_API_KEY}"
)
# -----------
# 谷歌云储存（用于中转 OCR(Vision) 接口所使用的 bucket）
# -----------
GOOGLE_STORAGE_MOEFLOW_VISION_TMP = {
    "JSON": "env_files/google_storage_service_account.json",
    "BUCKET_NAME": "moeflow",
    "GS_URL": "gs://moeflow",
}
# -----------
# EMAIL SMTP
# -----------
EMAIL_SMTP_HOST = "smtpdm.aliyun.com"
EMAIL_SMTP_PORT = 465
EMAIL_USE_SSL = True
EMAIL_ADDRESS = "no-reply@mail.moeflow.com"
EMAIL_USERNAME = "MoeFlow"
EMAIL_PASSWORD = env["EMAIL_PASSWORD"]
EMAIL_REPLY_ADDRESS = "reply@moeflow.com"
EMAIL_ERROR_ADDRESS = "error@moeflow.com"
# -----------
# Celery
# -----------
CELERY_BROKER_URL = (
    f"amqp://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASS']}"
    + f"@rabbitmq:5672/{APP_NAME}"
)
CELERY_BACKEND_URL = DB_URI
CELERY_MONGODB_BACKEND_SETTINGS = {
    "database": APP_NAME,
    "taskmeta_collection": "celery_taskmeta",
}
# -----------
# APIKit
# -----------
APIKIT_PAGINATION_PAGE_KEY = "page"
APIKIT_PAGINATION_LIMIT_KEY = "limit"
APIKIT_PAGINATION_DEFAULT_LIMIT = 30
APIKIT_PAGINATION_MAX_LIMIT = 100
APIKIT_ACCESS_CONTROL_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Requested-With",
]
