# Build and Run
#    docker build -t beanbot-lb . && docker run --env-file="./.env" beanbot-lb

FROM python:3.9

RUN \
  apt-get update -q && \
#   apt-get install -y && \
  apt-get autoremove 

WORKDIR /bot

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY beanbot/ beanbot/

CMD ["python", "-m", "beanbot"]