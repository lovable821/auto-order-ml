# Auto-Order MVP - CPU only
FROM python:3.10-slim

WORKDIR /app

# Build deps for lightgbm (wheels may need compile on some platforms)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY configs/ configs/
COPY data_sample/ data_sample/
COPY tests/ tests/
COPY main.py .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
