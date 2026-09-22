FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home bot

WORKDIR /app

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tests/ ./tests/
COPY zasob[y]/ ./zasoby/

ENV NUMBA_CACHE_DIR=/app/dane/.cache/numba
ENV PYTHONUNBUFFERED=1

USER bot

CMD ["python", "src/bot.py"]
