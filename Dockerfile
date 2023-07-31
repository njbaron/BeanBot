# Build and Run
#    docker build -t beanbot-lb . && docker run --env-file="./.env" beanbot-lb

FROM python:3.10

RUN \
  apt-get update -q && \
  apt-get install -y && \
  apt-get autoremove 

WORKDIR /bot

COPY . .

RUN pip install .

CMD ["beanbot"]