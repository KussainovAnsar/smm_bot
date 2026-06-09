FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY src ./src

# Run as a non-root user and pre-create the writable work dir.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/work/tmp \
    && chown -R appuser:appuser /app
USER appuser

# Bot uses long-polling: outbound connections only, no ports to expose.
CMD ["python", "-m", "src.smm_bot.bot"]
