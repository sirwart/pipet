
FROM python:3.6.1-slim

WORKDIR /app

ADD . /app

RUN pip install -r requirements.txt

EXPOSE 80

ENV FLASK_APP pipet/__init__.py

CMD ["flask", "run"]