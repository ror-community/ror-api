FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ES_VERSION=7.10.1

# System dependencies: Python 3.12 (matches CI/dev), build toolchain for
# mysqlclient/numpy/pandas, MySQL server, and utilities.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3.12-dev python3-pip \
        build-essential pkg-config \
        default-libmysqlclient-dev libmagic1 libcairo2-dev \
        mysql-server \
        git curl wget unzip ca-certificates tzdata sudo procps \
    && rm -rf /var/lib/apt/lists/*

# Provide a plain `python` pointing at 3.12
RUN ln -sf /usr/bin/python3.12 /usr/local/bin/python

# Elasticsearch 7.10.1 (matches docker-compose.yml + CI service)
RUN wget -q "https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ES_VERSION}-linux-x86_64.tar.gz" -O /tmp/es.tgz \
    && tar xzf /tmp/es.tgz -C /opt \
    && mv "/opt/elasticsearch-${ES_VERSION}" /opt/elasticsearch \
    && rm /tmp/es.tgz \
    && useradd -r -m -d /opt/elasticsearch-home elasticsearch \
    && mkdir -p /var/lib/elasticsearch /var/log/elasticsearch \
    && chown -R elasticsearch:elasticsearch /opt/elasticsearch /var/lib/elasticsearch /var/log/elasticsearch

COPY .cursor/elasticsearch.yml /opt/elasticsearch/config/elasticsearch.yml
RUN sed -i 's/^-Xms.*/-Xms512m/; s/^-Xmx.*/-Xmx512m/' /opt/elasticsearch/config/jvm.options \
    && chown elasticsearch:elasticsearch /opt/elasticsearch/config/elasticsearch.yml

# Ubuntu 24.04 ships a `ubuntu` user (uid 1000); grant passwordless sudo so
# start.sh can manage MySQL and Elasticsearch services.
RUN if ! id ubuntu >/dev/null 2>&1; then useradd -m -s /bin/bash ubuntu; fi \
    && echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

USER ubuntu
WORKDIR /workspace
