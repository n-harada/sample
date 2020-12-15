FROM ubuntu:16.04
# VOLUME /app
# RUN mkdir /app/django_project
COPY docker/back/requirements.txt app/requirements.txt

# Pythonインストール
RUN apt-get update && apt-get install -y software-properties-common && add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y python3.6 python3.6-dev python3-pip
RUN ln -sfn /usr/bin/python3.6 /usr/bin/python3 && ln -sfn /usr/bin/python3 /usr/bin/python && ln -sfn /usr/bin/pip3 /usr/bin/pip
WORKDIR /app
RUN python3 --version
RUN pip3 install --upgrade pip

# OCR用
RUN apt install mecab -y
RUN apt install libmecab-dev -y
RUN apt install mecab-ipadic-utf8 -y
RUN apt autoremove -y

# Ubuntuに必要なものインストール(エディタ、ロケール、言語設定)
RUN apt-get install vim -y
RUN apt-get update \
    && apt-get install -y locales \
    && locale-gen ja_JP.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL=ja_JP.UTF-8
RUN localedef -f UTF-8 -i ja_JP ja_JP.utf8

# AWS CLI
RUN apt-get install curl -y
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN apt install unzip
RUN unzip awscliv2.zip
RUN ./aws/install -i /usr/local/aws-cli -b /usr/local/bin

# for psycopg2
RUN apt install libpq-dev -y

# Pythonパッケージインストール
RUN apt install git -y
RUN pip3 install -r requirements.txt

RUN apt-get install -y libgl1-mesa-dev
RUN apt-get install postgresql -y
WORKDIR /app/django_project

