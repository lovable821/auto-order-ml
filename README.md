# Retail Demand Forecasting & Auto-Order System

A production-ready Python ML project for retail demand forecasting and automated reordering.

## Project Structure

```
auto-order-ml/
├── src/
│   ├── api/          # REST endpoints, request/response handling
│   ├── pipeline/     # Data ingestion, preprocessing, orchestration
│   ├── features/     # Feature engineering, feature store
│   ├── models/       # Demand forecasting models, training
│   ├── inventory/    # Stock management, order logic
│   └── policy/       # Ordering policies, business rules
├── configs/          # YAML configuration files
├── notebooks/        # Jupyter notebooks for exploration
├── tests/            # Test suite
├── main.py           # Entrypoint
├── requirements.txt
├── Dockerfile
└── README.md
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
```

## Usage

```bash
# Run full pipeline (forecast + auto-orders)
python main.py

# Train models only
python main.py --train

# Start REST API
python main.py --api
# or: uvicorn src.api.app:app --reload
```

## Configuration

Edit `configs/default.yaml` to adjust:

- Pipeline paths and batch size
- Feature lookback and target column
- Model type (prophet, arima, xgboost)
- Inventory safety stock and lead time
- Ordering policy rules

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

## Docker

```bash
docker build -t auto-order-ml .
docker run -p 8000:8000 auto-order-ml
```

## Architecture

- **Clean architecture**: domain logic isolated from I/O and frameworks
- **Modular design**: each module has a single responsibility
- **Config-driven**: behavior controlled via YAML configs

## License

Proprietary.
