FROM python:3.11-slim

LABEL maintainer="Viraly Team <support@viraly.io>"
LABEL description="AI-Powered Social Media Management Platform"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs && chmod 755 logs

RUN flask db upgrade || true

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

USER nobody

CMD ["gunicorn", "wsgi:app", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-"]