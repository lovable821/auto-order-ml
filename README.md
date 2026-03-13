# Retail Demand Forecasting & Auto-Order System

## 1. Project Overview

MVP for automated replenishment: predict tomorrow’s demand per store × SKU and recommend order quantities. Balances availability and waste.

**What it does:**

- **Next-day demand forecasting** — Predicts tomorrow's demand for each store–SKU combination
- **Inventory-aware ordering** — Uses current stock and forecast to compute order quantities
- **Expiration-aware stock control** — Caps inventory by shelf life to reduce waste
- **Configurable ordering policies** — Three modes: service-first, waste-first, balanced
- **Evaluation through inventory simulation** — FIFO simulation to validate policies on historical demand

---

## 2. Business Problem

Retailers balance two costs: stockouts (lost sales) and waste (expired or excess stock). Order too little and you lose sales; order too much and you write off product.

A good forecast is necessary but not sufficient. If we predict 100 units, we still need to decide how much to order given current stock, shelf life, and whether we care more about availability or waste. This system does both: forecast demand and recommend order quantities.

---

## 3. System Architecture

The pipeline runs end-to-end in sequence:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│  API Ingestion  │────▶│  Data Cleaning  │────▶│ Censored Demand      │
│  (sales, inv,   │     │  (normalize,     │     │ Adjustment           │
│   products,     │     │   outliers)     │     │ (flag/impute)        │
│   losses)       │     └─────────────────┘     └──────────┬──────────┘
└─────────────────┘                                          │
                                                             ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│   Inventory     │◀────│ Order           │◀────│ Demand Forecast      │
│   Simulation    │     │ Optimization    │     │ (LightGBM)           │
└─────────────────┘     └────────┬────────┘     └──────────┬──────────┘
                                 │                          │
                                 │                ┌─────────▼─────────┐
                                 └────────────────│ Feature           │
                                                  │ Engineering       │
                                                  │ (lags, rolling,   │
                                                  │  calendar)        │
                                                  └───────────────────┘
```

**Pipeline stages:**

1. **API ingestion** — Fetch sales, inventory, products, losses from Forecasto API or CSV
2. **Data cleaning** — Normalize columns, remove outliers (IQR), optional missing-date fill
3. **Censored demand adjustment** — Flag or impute demand when stockouts occurred
4. **Feature engineering** — Lags, rolling stats, calendar features
5. **Demand forecasting** — LightGBM model for next-day demand per store × SKU
6. **Order optimization** — Compute recommended order quantities
7. **Policy adjustment** — Load ordering policy from config (service-first, waste-first, balanced)
8. **Inventory simulation** — Run FIFO simulation to evaluate policy performance

---

## 4. Data Sources

Data is loaded from the Forecasto API (api.forecasto.ru) or from CSV files:

| Source | Endpoint | Description |
|--------|----------|-------------|
| Sales | `/sales` | Historical sales by date, SKU, quantity |
| Inventory | `/inventory/stock` | Current stock levels by SKU |
| Products | `/backend/delivery_info/api/v1/GetAll` | Product properties (ExpirationDays, MinStockLevel, etc.) |
| Losses | `/loss/getall` | Waste and write-off records |

These datasets are joined on SKU and date to produce a modeling dataset. Sales are aggregated by store × SKU × date. Inventory is used for censoring and order optimization. Product properties provide `ExpirationDays` for shelf-life constraints.

---

## 5. Handling Censored Demand

If a product is out of stock, sales equal what we had, not what customers wanted. True demand is hidden.

We join sales with inventory by date and SKU. When balance is zero at end of day, that day’s sales are censored. We flag those rows and either exclude them from training or impute with a rolling mean of past demand. Training on raw censored data makes the model think demand is lower than it is, so we’d under-order.

---

## 6. Demand Forecasting Model

**Architecture:** LightGBM gradient boosting regression.

**Features:**

- **Lag features** — Demand at t−1, t−2, t−3 (configurable, e.g. 1, 7, 14)
- **Rolling statistics** — Rolling mean and std over 3–6 day windows
- **Temporal features** — `day_of_week`, `month`, `day_of_month`, `is_weekend`
- **SKU encoding** — Categorical encoding for product differentiation

The model predicts next-day demand per store × SKU. The last row per (store_id, sku) is used as input to generate tomorrow's forecast.

---

## 7. Order Optimization

Base-stock policy:

```
target_stock = forecast + safety_stock
order_qty = max(target_stock − current_stock, 0)
```

**Safety stock** depends on demand volatility and is configurable via `reorder_point_multiplier` and `safety_stock_days`. Higher volatility increases safety stock to buffer against forecast error.

The implementation orders to cover forecast (`need = forecast − stock`), applies min/max order constraints, and caps by expiration (Section 8).

---

## 8. Expiration-Aware Inventory Control

Products with limited shelf life should not be over-ordered. Stock that exceeds sellable quantity before expiration becomes waste.

**Logic:**

```
max_stock = expiration_days × forecast_demand
waste_cap = max(0, max_stock − current_stock)
order_qty = min(need, waste_cap)
```

Order quantity is capped so that `stock + order_qty` does not exceed the amount of product that can be sold before expiration. This reduces write-offs and spoilage.

---

## 9. Dynamic Inventory Policies

Three operating modes adjust the trade-off between service level and waste:

| Mode | Objective | Behavior |
|------|-----------|----------|
| **Service-first** | Minimize stockouts | Order full need; no expiration cap |
| **Waste-first** | Minimize excess and expiration | Use 50% of effective shelf life as cap |
| **Balanced** | Compromise | Standard cap: `expiration_days × forecast` |

Policies adjust the effective cap on inventory. Service-first prioritizes availability; waste-first minimizes overstock; balanced balances both.

---

## 10. Inventory Simulation

We run a day-by-day simulation: each day we age stock, satisfy demand (FIFO), record stockouts and waste, then place orders using our policy. Batches expire when they exceed shelf life.

This lets us test policies on historical demand without going live. A good forecast can still lead to bad outcomes if we order too much (waste) or too little (stockouts). Simulation gives service level, lost sales, waste, and turnover so we can compare policies.

---

## 11. Evaluation Metrics

**Forecasting metrics:**

- **WAPE** (Weighted Absolute Percentage Error) — Primary metric; scale-invariant
- **Bias** — Systematic over- or under-forecasting (positive = over-forecast)

---

## 12. Project Structure

```
├── src/
│   ├── api/              # Forecasto API client
│   ├── config/           # Logging configuration
│   ├── evaluation/       # Visualization (actual vs predicted, inventory, etc.)
│   ├── features/         # Feature engineering (lags, rolling, calendar)
│   ├── inventory/        # Order optimizer, order simulation
│   ├── models/            # LightGBM forecaster, WAPE/Bias metrics
│   ├── pipeline/         # Orchestrator, stages, ingestion
│   └── policy/           # OrderPolicy, PolicyMode
├── configs/
│   └── default.yaml      # Pipeline configuration
├── data_sample/          # Sample CSV data
├── scripts/
│   ├── run_simulation.py
│   └── run_visualizations.py
├── tests/
├── main.py               # Entrypoint
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 13. Running the Project

**Local execution:**

```bash
pip install -r requirements.txt
python main.py
```

**CLI options:**

```bash
python main.py --part-a           # Demand forecast only
python main.py --part-b           # Order optimization only
python main.py --part-b --policy waste_first
python main.py --train            # Training through forecast
python main.py --simulate         # Inventory simulation demo
python main.py --visualize        # Generate charts
```

**Docker:**

```bash
docker build -t auto-order .
docker run auto-order
```

CPU only. No GPU required.

---

## 14. Results & Insights

Results below are from a full pipeline run on the sample dataset (24 sales rows, 2 SKUs), balanced policy.

| Metric | Value | Description |
|--------|-------|-------------|
| WAPE | 0.163 | Weighted absolute % error; lower is better |
| Bias | −0.163 | Negative = under-forecast |
| Service Level | 90% | Share of demand satisfied |
| Waste Rate | 0% | Expired/written-off stock as % of demand |
| Lost Sales | 174 | Units not sold due to stockouts |

**Metric notes.** WAPE is scale-invariant so we can compare across SKUs. Bias shows we’re slightly under-forecasting (negative). Service level = 1 − lost_sales / total_demand. Waste rate = waste / total_demand. Lost sales are the main cost when we under-order.

**Forecast.** The model gives different predictions per SKU because of lag and rolling features. Without SKU or product features, forecasts would collapse to one value. Short lags (1, 2, 3) and small rolling windows (3, 6) suit sparse data; longer windows would drop too many rows.

**Model behavior.** We do better when demand is stable and recent history is available. We do worse on sudden spikes or new SKUs with little history. Censored demand correction helps when there are many stockouts; otherwise the model learns from truncated demand.

**Policy impact.** Balanced: ~90% service, 0 waste in this run. Service-first: higher service, more waste when we over-forecast. Waste-first: less waste, more stockouts on spikes. The trade-off is direct: service-first ignores the expiration cap; waste-first uses half the shelf life.

---

## 15. Technical Challenges & Solutions

**Censored demand.** When we’re out of stock, sales = what we had, not what people wanted. Training on that underestimates demand. We join sales with inventory, flag days where balance was zero, and either exclude or impute those rows. That way the model doesn’t learn from truncated demand.

**Noisy data.** Retail data has missing dates, outliers, inconsistent column names. We use IQR for outliers, optional missing-date fill, and a normalization layer so API and CSV both map to the same schema.

**Sparse SKU demand.** Many SKUs have few rows. Long lags (7, 14) create too many NaNs. We use short lags (1, 2, 3) and small rolling windows (3, 6), plus relaxed tree params (`min_data_in_leaf=2`) so we can still split by SKU.

**Forecast vs orders.** A good forecast doesn’t guarantee good orders. We separate the two: the model forecasts, the optimizer decides order qty with expiration caps and policy mode. That lets us tune ordering without retraining.

**Policy flexibility.** Priorities change. Policy mode lives in config; we switch service-first / waste-first / balanced without touching code.

---

## 16. Design Decisions

- **LightGBM** — Tabular data, mixed features, small sample. LightGBM handles that well and is fast. Prophet/ARIMA didn’t fit our store×SKU setup.

- **Censored demand** — We had to fix stockout days or the model would under-forecast. Flagging or imputing those rows reduced bias.

- **Modular pipeline** — Each stage is its own module. Easier to test, swap, and run experiments. Config drives behavior.

- **Simulation** — We needed a way to test policies without going live. FIFO + batch expiration approximates real behavior; we get service level, waste, turnover before changing anything.

- **Config-driven policies** — Mode and params in YAML. Change behavior without code or redeploy.

---

## 17. Future Improvements

- **Hierarchical forecasting** — Aggregate forecasts across product groups; reconcile with SKU-level
- **Probabilistic demand** — Quantile forecasts or full distributions for risk-aware ordering
- **Reinforcement learning** — Learn ordering policy from reward (service level, waste) instead of rule-based
- **Automated hyperparameter tuning** — Optuna or similar for LightGBM and feature selection
- **Lead time modeling** — Explicit lead time in order optimization

---

## 18. Author

Technical assignment for retail demand forecasting and automated reordering.
