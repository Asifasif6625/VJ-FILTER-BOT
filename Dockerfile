# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

RUN pip3 install --no-cache-dir -U pip \
    && pip3 install --no-cache-dir -U -r /requirements.txt

WORKDIR /VJ-FILTER-BOT

COPY CloneTechVJ /VJ-FILTER-BOT/CloneTechVJ
COPY database /VJ-FILTER-BOT/database
COPY plugins /VJ-FILTER-BOT/plugins
COPY TechVJ /VJ-FILTER-BOT/TechVJ
COPY *.py logging.conf requirements.txt /VJ-FILTER-BOT/

CMD ["python", "-B", "bot.py"]

