FROM python:3.14.0-alpine3.21

WORKDIR /usr/src/app

ENV BOT_TOKEN=""

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]