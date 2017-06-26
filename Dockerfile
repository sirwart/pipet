FROM python:3.6.1

RUN groupadd -r pipet && useradd -r -g pipet pipet

ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on

# grab gosu for easy step-down from root
# grab tini for signal processing and zombie killing
RUN set -x \
    && export GOSU_VERSION=1.10 \
    && export TINI_VERSION=v0.14.0 \

    && apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/* \

    && wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture)" \
    && wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture).asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --keyserver ha.pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu \
    && rm /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && gosu nobody true \

    && wget -O /usr/local/bin/tini "https://github.com/krallin/tini/releases/download/$TINI_VERSION/tini" \
    && wget -O /usr/local/bin/tini.asc "https://github.com/krallin/tini/releases/download/$TINI_VERSION/tini.asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --keyserver ha.pool.sks-keyservers.net --recv-keys 6380DC428747F6C393FEACA59A84159D7001A4E5 \
    && gpg --batch --verify /usr/local/bin/tini.asc /usr/local/bin/tini \
    && rm /usr/local/bin/tini.asc \
    && chmod +x /usr/local/bin/tini \
    && tini -h \

    && rm -r "$GNUPGHOME" \
    && apt-get purge -y --auto-remove wget

WORKDIR /app

# We need uwsgi for production deploy
RUN pip install --no-cache-dir uwsgi==2.0.15

COPY requirements.txt /app
RUN pip install -r requirements.txt

ADD . /app

ENV PORT=8000 \
    UWSGI_MASTER=true \
    UWSGI_MODULE=pipet:app \
    UWSGI_DIE_ON_TERM=true \
    UWSGI_ENABLE_THREADS=true \
    UWSGI_NEED_APP=true \
    UWSGI_LAZY_APPS=true

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD [ "uwsgi" ]
