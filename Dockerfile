FROM python:3.11

LABEL project="moeflow-backend"

COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ARG MOEFLOW_BUILD_ID=unknown
ENV MOEFLOW_BUILD_ID=${MOEFLOW_BUILD_ID}

COPY . /app
WORKDIR /app

EXPOSE 5000
