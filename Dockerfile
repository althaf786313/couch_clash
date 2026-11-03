# COUCH CLASH — Diecast Duel
# No build step, no pip install: Python stdlib + vendored segno only.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app
COPY . /app

# Render / Railway / Fly / Cloud Run all inject PORT; server.py binds 0.0.0.0:$PORT.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import os,urllib.request; p=os.environ.get('PORT','8000'); urllib.request.urlopen('http://127.0.0.1:'+p+'/api/health', timeout=3).read()" || exit 1

CMD ["python3", "server.py"]
