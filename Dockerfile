FROM python:3.11

LABEL project="moeflow-backend"

ARG MOEFLOW_BUILD_ID=unknown
ENV MOEFLOW_BUILD_ID=${MOEFLOW_BUILD_ID}

COPY . /app
WORKDIR /app
EXPOSE 5000

RUN pip install -r requirements.txt
