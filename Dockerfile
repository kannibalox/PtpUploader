FROM python:3.9

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client sqlite3 mariadb-client mpv imagemagick mediainfo \
    && rm -rf /var/lib/apt/lists/*

# Optional dependencies
RUN pip install --no-cache-dir psycopg2 transmissionrpc

WORKDIR /usr/src/app

ENV PTPUP_WORKDIR /data

EXPOSE 8000

COPY . .

RUN pip install --no-cache-dir .
CMD [ "bash", "-c", "python src/manage.py migrate && python src/manage.py runuploader 0.0.0.0:8000"]
