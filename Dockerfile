FROM ubuntu:18.04
LABEL author="Edoardo De Din" 
LABEL author_contact="ededin@eonerc.rwth-aachen.de"

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
WORKDIR /powerflow
COPY requirements.txt .

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install build-essential git -y
RUN apt install python3-pip -y  \
    && pip3 install setuptools \
    && pip3 install --upgrade pip \
    && pip3 install wheel \
    && pip3 install -r requirements.txt