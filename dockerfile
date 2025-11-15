ARG BOT_TOKEN

FROM ubuntu:latest
WORKDIR /usr/src/app

ENV BOT_TOKEN=${APP_VERSION}

COPY . .

CMD ["pip", "install", "-r", "requirements.txt"]

CMD ["python", "./main.py"]