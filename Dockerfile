FROM python:3.10

RUN \
  apt-get update -q && \
  apt-get install -y && \
  apt-get autoremove 

WORKDIR /bot

COPY . .

RUN pip install -e .

CMD ["beanbot"]