FROM python:3.11-slim

RUN apt update && apt install -y curl nginx

COPY ./django-server /app
COPY ./requirements.txt /app/requirements.txt
COPY ./run.sh /app/run.sh
COPY ./recommendation /app/recommendation
COPY ./nginx-server/default.conf /etc/nginx/conf.d/default.conf

WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*
    
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-use-pep517 lightfm

RUN pip install -r requirements.txt

RUN chmod +x run.sh
CMD ["./run.sh"]