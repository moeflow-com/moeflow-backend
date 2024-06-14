
## Version 1.1.2

https://github.com/moeflow-com/moeflow-backend/releases/tag/v1.1.2

- upgrade python and deps
- ruff / CI
- move DB migration to manage.py

### Version.1.0.1

1. 修改部分没做本地化的位置（例如：首页、邮件），方便修改网站名称、标题、域名等信息。
2. 调整 config.py 中的配置格式，部分配置有默认值可选。
3. 调整阿里云 OSS 相关域名输出格式，私有读写模式下缩略图、下载等位置正常显示
4. 调整输出的翻译文本格式为 `utf-8`
5. 调整创建项目、创建团队时的部分参数，减少前端需配置的默认值。
6. 修改后端首页模版、增加 404 跳转到首页的代码。方便将前后端项目进行合并。（相关操作说明请参考前端帮助文件中对应段落！）


### Version 1.0.0

萌翻前后端开源的首个版本

