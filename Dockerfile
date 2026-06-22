FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Persistent volume mount-point for state file
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "src.main"]
# Default: run in loop mode. Pass "once" for a single scan.
CMD ["loop"]
