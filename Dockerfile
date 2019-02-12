FROM ubuntu:16.04

ENV TOR_VERSION=7.0.11 GECKO_VERSION=v0.18.0 USER_NAME=tordocker TB_SELENIUM_TAR=tor_selenium_crawler.tar.gz DISPLAY=:0

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip firefox xvfb xserver-xephyr vnc4server vim xrdp xfce4-terminal

RUN pip3 install --upgrade pip && \
    pip3 install pyvirtualdisplay selenium && \
    pip3 install -U requests[socks]

RUN useradd ${USER_NAME} -m -s /bin/bash

ENV HOME=/home/${USER_NAME}

COPY TBB/tor-browser-linux64-${TOR_VERSION}_en-US.tar.xz /home/${USER_NAME}
COPY TBSEL/${TB_SELENIUM_TAR} /home/${USER_NAME}
COPY GECKO/geckodriver-${GECKO_VERSION}-linux64.tar.gz /home/${USER_NAME}

RUN tar xfJ /home/${USER_NAME}/tor-browser-linux64-${TOR_VERSION}_en-US.tar.xz -C /home/${USER_NAME}/ && \
    tar xf /home/${USER_NAME}/geckodriver-${GECKO_VERSION}-linux64.tar.gz -C /usr/local/bin/ && \
    tar xf /home/${USER_NAME}/${TB_SELENIUM_TAR} -C /home/${USER_NAME}/

RUN rm /home/${USER_NAME}/tor-browser-linux64-${TOR_VERSION}_en-US.tar.xz \
       /home/${USER_NAME}/geckodriver-${GECKO_VERSION}-linux64.tar.gz \
       /home/${USER_NAME}/${TB_SELENIUM_TAR}

RUN chown ${USER_NAME}:${USER_NAME} /home/${USER_NAME}

USER ${USER_NAME}

RUN mkdir /home/${USER_NAME}/shared_dir
