# Auto-Order MVP – Test Assignment

## Overview

Build an MVP for automated ordering with three parts:

- **Part A**: Demand forecast for tomorrow (per store × SKU)
- **Part B**: Order quantity for tomorrow (`order_qty`)
- **Part C**: Dynamic policy (OOS vs waste balance)

---

## Part A: Demand Forecast for Tomorrow

### Goal

Build a model that predicts **tomorrow's demand** for each **store × SKU**.

### Data Sources (Forecasto API – api.forecasto.ru)

#### 1. Sales

**Endpoint:** `https://api.forecasto.ru/sales`

**Request (POST, JSON):**
```json
{
  "token": "string",
  "START_DATE": "string",
  "FINISH_DATE": "string"
}
```
- Date format: `dd.MM.yyyy` (e.g. `05.03.2026`)

**Response:**
```json
[
  {
    "Период": "05.03.2026",
    "Номенклатура": "Pie \"Russian with berry-fruit filling\", 0.300 kg",
    "Количество": 1,
    "Сумма": 153.64,
    "ВидНоменклатуры": "Product",
    "Код": "ПРЯФ*",
    "Артикул": "ПРЯФ*",
    "Группа": "Pies, pastries, donuts",
    "Вес": null
  }
]
```

| Field (RU) | English | Description |
|------------|---------|-------------|
| Период | date | Sale date |
| Номенклатура | product_name | Product name |
| Количество | quantity | Quantity sold |
| Сумма | amount | Revenue |
| Код | code | SKU code |
| Артикул | article | Article number |
| Группа | product_group | Product group |

---

#### 2. Inventory (Stock)

**Endpoint:** `https://api.forecasto.ru/inventory/stock`

**Request (POST, JSON):**
```json
{
  "token": "",
  "Date": ""
}
```

**Response:**
```json
[
  {
    "Date": "05.03.2026",
    "Code": "ТВИ5",
    "Name": "Cherry Cake 0.500 kg",
    "balance": 0
  }
]
```

| Field | Description |
|-------|-------------|
| Date | Snapshot date |
| Code | SKU code |
| Name | Product name |
| balance | Current stock |

---

#### 3. Product Properties

**Endpoint:** `https://api.forecasto.ru/backend/delivery_info/api/v1/GetAll`

**Request (POST, JSON):**
```json
{
  "token": ""
}
```

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "item_code": "РТ-00000250",
      "item_name": "Belyash Omsky 0.4kg",
      "item_information": [
        {"ExpirationDays": "7"},
        {"DaysCount": 1},
        {"MinStockLevel": 0},
        {"ProductGroup": "FROZEN SEMI-FINISHED PRODUCTS"},
        {"UnitOfMeasure": "шт"},
        {"Needfridge": false},
        {"Needfreezer": false}
      ]
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| ExpirationDays | Shelf life (days) |
| MinStockLevel | Minimum stock level |
| ProductGroup | Product group |
| UnitOfMeasure | Unit of measure |

---

#### 4. Loss / Waste

**Endpoint:** `https://api.forecasto.ru/loss/getall`

**Request (POST, JSON):**
```json
{
  "token": "string",
  "Date": "string"
}
```

**Response:**
```json
[
  {
    "Date": "04.03.2026",
    "item_id": "КС",
    "loss": 1,
    "totalloss": 163.11,
    "reason": "loss"
  }
]
```

| Field | Description |
|-------|-------------|
| Date | Loss date |
| item_id | SKU code |
| loss | Quantity wasted |
| totalloss | Financial loss |
| reason | Reason (e.g. "loss") |

---

### Metrics

- **Primary:** WAPE (Weighted Absolute Percentage Error)
- **Secondary:** Bias

### Censoring

Client data is often noisy and needs preprocessing. A clear approach to demand censoring is required (e.g. handling stockouts, truncation, outliers).

---

## Part B: Order Quantity for Tomorrow

### Goal

Implement a function that returns recommended **order_qty** for tomorrow.

### Inputs

1. Demand forecast for tomorrow  
2. Current stock  
3. Expiration days (shelf life)

### Constraint

Accurate forecast ≠ best order. Need a deliberate balance between:

- **Out-of-stock (OOS)** – lost sales
- **Write-offs / overstock** – waste and excess inventory

---

## Part C: Dynamic Forecast Policy

### Goal

Implement a policy with **3 configurable modes**:

| Mode | Objective |
|------|-----------|
| **Service-first** | Minimize OOS |
| **Waste-first** | Minimize write-offs / excess |
| **Balanced** | Compromise between OOS and waste |

This lets the model adapt to the client’s current priorities.

---

## Deliverables

- Repository with working code
- Docker build (CPU only; mention if GPU is required)
