FROM ubuntu:latest
LABEL authors="s-storozhuk"

RUN mkdir /app

RUN apt-get update && apt-get upgrade -y && \
  apt-get -y install \
    pip \
    bash \
    curl \
    git \
    htop \
    python3-aiofiles \
    vim \
    openssl \
    libssl-dev \
  && apt-get clean

COPY /my_store /app/my_store

COPY ./requirements.txt /app/

ENV PYTHONPATH "${PYTHONPATH}:/app"
ENV PYTHONUNBUFFERED=TRUE

RUN cd /app && pip install -r requirements.txt

WORKDIR /app
