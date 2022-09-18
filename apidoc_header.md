## HTTP status code 约定

|status code| 内容
|---|---
|200-299|成功的请求
|400-499|失败的请求，body将包含json格式的错误详细内容
|500-599|服务器错误

## 错误格式约定

**一般错误格式**

|名称    |内容
|---    |---
|code   |错误的具体代码
|error  |错误的类名
|message|内容支持i18n，一般可以直接返回给用户

```json
{
    "code": 2,
    "error": "NoPermissionError",
    "message": "抱歉，您没有权限。"
}
```
**ValidateError(#2)错误格式**

错误信息包含于字段名的数组内

```json
{
    "code": 2,
    "error": "ValidateError",
    "message": {
        "email": [
            "此邮箱未注册"
        ],
        "password": [
            "必填"
        ]
    }
}
```

