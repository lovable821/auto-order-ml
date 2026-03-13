# Retail Demand Forecasting & Auto-Order System
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (e.g. for prophet)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY configs/ configs/
COPY main.py .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Default: run main pipeline; override for API
CMD ["python", "main.py"]
