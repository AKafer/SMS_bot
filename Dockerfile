FROM ubuntu:latest
LABEL authors="s-storozhuk"

WORKDIR /app

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

COPY /my_store /app

COPY requirements.txt /app

RUN pip install -r requirements.txt