FROM ubuntu:18.04
MAINTAINER Edoardo De Din ededin@eonerc.rwth-aachen.de

RUN apt-get update -y \
    && apt-get upgrade -y \ 
    && apt-get install build-essential -y \
    && apt install python3-pip -y  \
    && apt-get install python3-venv -y \
    && apt-get install sudo -y 

# ENV VIRTUAL_ENV=/opt/venv
# RUN python3 -m virtualenv --python=/usr/bin/python3 $VIRTUAL_ENV
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"
EXPOSE 1883

COPY setup/requirements_docker.txt .
RUN pip3 install -r requirements_docker.txt