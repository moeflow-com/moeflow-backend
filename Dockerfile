FROM python:3.8.13

LABEL project="moeflow-backend"

COPY . /app
WORKDIR /app
EXPOSE 5000

RUN pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/