FROM python:3.6.1-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
EXPOSE 5000
ENV FLASK_APP pipet/__init__.py
CMD ["flask", "run", "-h", "0.0.0.0"]
