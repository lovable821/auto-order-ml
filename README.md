# Auto-Order MVP – Retail Demand Forecasting

MVP for automated ordering: demand forecast (Part A), order quantity (Part B), and dynamic policy (Part C).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # Add FORECASTO_TOKEN for API access
```

## Usage

```bash
# Full pipeline (ingestion → forecast → orders → simulation)
python main.py

# Part A: demand forecast for tomorrow
python main.py --part-a

# Part B: order quantity for tomorrow
python main.py --part-b
python main.py --part-b --policy waste_first   # service_first | waste_first | balanced

# Training only
python main.py --train

# Inventory simulation demo
python main.py --simulate

# Generate charts
python main.py --visualize
```

## Configuration

Edit `configs/default.yaml`:

- `data_source`: "csv" or "api"
- `pipeline.data_path`: path to data (default: data_sample)
- `policy.policy_mode`: service_first | waste_first | balanced
- `reproducibility.random_seed`: for reproducibility

## Project Structure

```
src/
  api/          # Forecasto API client (api.forecasto.ru)
  pipeline/     # Orchestrator, stages, ingestion
  features/     # Feature engineering
  models/       # LightGBM forecaster, metrics
  inventory/    # Order optimizer, simulation
  policy/       # OrderPolicy, PolicyMode
  evaluation/   # Visualization
configs/        # YAML config
data_sample/    # Sample CSV data
```

## Docker

```bash
docker build -t auto-order-mvp .
docker run auto-order-mvp
```

CPU only. No GPU required.

## Tests

```bash
pytest tests/ -v
```

## Assignment Parts

| Part | Description |
|------|-------------|
| A | Demand forecast for tomorrow (store × SKU), WAPE/Bias metrics |
| B | Order quantity from forecast + stock + expiration |
| C | Policy modes: service-first, waste-first, balanced |
