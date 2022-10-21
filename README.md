# 萌翻后端项目

由于此版本调整了部分API接口，**请配合萌翻前端Version.1.0.1版本使用！**直接使用旧版可能在修改（创建）团队和项目时报错。
此版本需配置**阿里云OSS**作为文件存储。如果需要使用其他文件存储方式，可以选择使用以下的分支版本：

* **本地硬盘存储** [`scanlation/moetran-local-backend`](https://github.com/scanlation/moetran-local-backend)

## 安装步骤

1. 安装 Python 3.8.13 版本以上，3.10 版本以下，推荐 `3.9.2`
2. 依赖环境MangoDB、Erlang、RabbitMQ
3. `pip install -r requirements.txt` （这一步如果Windows有报错，请在环境变量里面加 `PYTHONUTF8=1` ）
4. 以 `/config.py` 为模板创建 `/configs/dev.py` 用于开发（此目录已被 git ignore）
5. 开发时，请直接在 `/configs/dev.py` 文件里面修改必填的配置
6. 运行前注意配置环境变量 `CONFIG_PATH=../configs/dev.py`
7. 运行主进程： `python manage.py run`
8. 在 `DEBUG` 开启的情况下，注册等验证码信息，直接看命令行输出的日志信息。
9. *(可选)* 导入、导出等功能需要依赖两个celery worker进程，调试时可按另附的步骤启动。

## 配置Celery

1. 如果使用Windows跑Celery Worker，需要先安装 `eventlet` 并修改参数，否则会提示： `not enough values to unpack (expected 3, got 0)`
2. *(可选)* Windows安装 `eventlet` 请执行： `pip install eventlet`
3. 两个worker需要启动两个命令行（**这里的方案使用 Windows 的 Powershell 举例**），运行前需配置环境变量：`CONFIG_PATH=../configs/dev.py`
4. 启动主要 Celery Worker (发送邮件、分析术语)，请执行：`celery -A app.celery worker -n default -P eventlet --loglevel=info`
5. 启动输出用 Celery Worker (导入项目、生成缩略图、导出翻译、导出项目)，请执行：`celery -A app.celery worker -Q output -n output -P eventlet --loglevel=info`
6. 非Windows环境如果有报错，请去掉命令中的 `-P eventlet` 一段。


## 版本修改内容一览

### Version.1.0.1010

1. 修改部分没做本地化的位置（例如：首页、邮件），方便修改网站名称、标题、域名等信息。
2. 调整config.py中的配置格式，部分配置有默认值可选。
3. 调整阿里云OSS相关域名输出格式，私有读写模式下缩略图、下载等位置正常显示
4. 调整输出的翻译文本格式为 `utf-8`
5. 调整创建项目、创建团队时的部分参数，减少前端需配置的默认值。
