FROM python:3.9-slim

RUN apt-get update
RUN apt-get -y install locales && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

RUN apt-get install -y \
    vim \
    less \
    libasound2-dev \
    iputils-ping \
    nano \
    tree \
    git \
    curl \
    rsync
    
RUN pip install --upgrade pip setuptools

RUN pip install \
    requests \
    watchdog \
    flask \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    python-dotenv

# ユーザ関連
RUN groupadd -g 1000 appgroup && useradd -u 1000 -g appgroup -d /home/appuser -m appuser
WORKDIR /home/appuser/app

USER appuser