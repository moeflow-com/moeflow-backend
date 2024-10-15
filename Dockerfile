FROM python:3.11

LABEL project="moeflow-backend"

COPY . /app
WORKDIR /app
EXPOSE 5000

RUN pip install -r requirements.txt
RUN make babel-update-mo
