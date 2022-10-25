# ===========
# 脱敏的生产环境配置（严禁记录密钥）
# 开发测试配置可放在 configs 文件夹下（已 gitignore）或项目外
# ===========
from os import environ as env

# -----------
# 基础设置
# -----------
APP_NAME = "moeflow"
APP_VERSION = "1.0.1"
APP_SITE_NAME = env.get("APP_SITE_NAME", "萌翻")
APP_SITE_URL = env.get("APP_SITE_URL") # 配置前端域名（邮件和首页跳转会用到）
SECRET_KEY = env["SECRET_KEY"] # 必填 - 密钥
# 密钥：没有明确格式，只用来对密码加密（修改密钥后，所有之前的用户就无法登录了，需要重置密码）
DEBUG = False
TESTING = False
MAX_CONTENT_LENGTH = 20 * 1024 * 1024
# -----------
# Mongo 数据库
# -----------
DB_URI = ( # 必填 - MangoDB连接串
    # 正式环境请使用下方的写法
    f"{env['MONGODB_URL']}/{APP_NAME}?authSource=admin"
    # 本地测试，如果需要快速链接，请使用下方的写法
    # f"mongodb://127.0.0.1:27017/{APP_NAME}?authSource=admin"
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
OSS_ACCESS_KEY_ID = env["OSS_ACCESS_KEY_ID"] # 必填
OSS_ACCESS_KEY_SECRET = env["OSS_ACCESS_KEY_SECRET"] # 必填
OSS_ENDPOINT = env.get("OSS_ENDPOINT", "https://oss-cn-shanghai.aliyuncs.com/")  # 线上需要修改成内网端点
OSS_BUCKET_NAME = env.get("OSS_BUCKET_NAME", APP_NAME)
# OSS_DOMAIN 可能绑定在 CDN 来加速 OSS，并开启了 CDN 的[阿里云 OSS 私有 Bucket 回源]和[URL 鉴权]，
# 此时需要设置 OSS_VIA_CDN = True，将通过 CDN 的 URL 鉴权方式来生成 URL，而不用 OSS 的 URL 签名
OSS_VIA_CDN = False
# CDN URL 鉴权主/备 KEY
CDN_URL_KEY_A = env.get("CDN_URL_KEY_A", "")
CDN_URL_KEY_B = env.get("CDN_URL_KEY_B", "")  # 备 KEY 暂未用到
# 用户自定义域名（未设置则填写阿里云提供的 OSS 域名）
OSS_DOMAIN = env["OSS_DOMAIN"] # 必填
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
    "JSON": "env_files/google_storage_service_account.json",
    "BUCKET_NAME": APP_NAME,
    "GS_URL": "gs://" + APP_NAME,
}
# -----------
# EMAIL SMTP
# -----------
EMAIL_SMTP_HOST = env.get("EMAIL_SMTP_HOST", "smtp.163.com") # 必填 - SMTP服务器地址
EMAIL_SMTP_PORT = env.get("EMAIL_SMTP_PORT", 465) # 必填 - SMTP服务器端口
EMAIL_USE_SSL = True
EMAIL_ADDRESS = env.get("EMAIL_ADDRESS", "no-reply@moetran.com")
EMAIL_USERNAME = env.get("EMAIL_USERNAME", "MoeFlow") # 必填 - SMTP服务器用户名，通常是邮箱全称
EMAIL_PASSWORD = env.get("EMAIL_PASSWORD", "") # 必填 - SMTP服务器密码
EMAIL_REPLY_ADDRESS = env.get("EMAIL_ADDRESS", "reply@moeflow.com")
EMAIL_ERROR_ADDRESS = env.get("EMAIL_ADDRESS", "error@moeflow.com")
# -----------
# Celery
# -----------
CELERY_BROKER_URL = (
    # 大部分场景建议填写完整的地址
    f"{env['RABBITMQ_URL']}/{APP_NAME}"
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
APIKIT_PAGINATION_DEFAULT_LIMIT = 30 #每页条目数
APIKIT_PAGINATION_MAX_LIMIT = 100
APIKIT_ACCESS_CONTROL_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Requested-With",
]

# -----------
# 配置可访问域名
# 填写 * 为所有域名都正常使用
# 填写单个域名格式为 https://www.moetran.com
# 填写多个域名时用半角逗号分割
# -----------
allow_origin = env.get("ALLOW_ORIGIN", "*")
if allow_origin == "*":
    APIKIT_ACCESS_CONTROL_ALLOW_ORIGIN = allow_origin
elif allow_origin.count(',') > 0:
    allow_origins = allow_origin.split(',')
    APIKIT_ACCESS_CONTROL_ALLOW_ORIGIN = allow_origins