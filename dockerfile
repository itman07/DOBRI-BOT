FROM python:3.14.0-alpine3.21

WORKDIR /usr/src/app

ENV BOT_TOKEN="f9LHodD0cOIPRyzuSVEQMG9_pjAcwioS7IRzEqf_LJi82cOb4D88uusFdBkEPa_VUZhp-MP3O3vUCLoNRGHc"

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]