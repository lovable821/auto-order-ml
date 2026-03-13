"""FastAPI application - REST API for forecasts and orders."""

from fastapi import FastAPI

app = FastAPI(
    title="Retail Demand Forecasting API",
    version="0.1.0",
    description="Forecast demand and manage auto-orders",
)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/forecast/{product_id}")
def get_forecast(product_id: str) -> dict:
    """Get demand forecast for a product. Placeholder."""
    return {"product_id": product_id, "forecast": []}


@app.post("/orders")
def create_orders() -> dict:
    """Trigger auto-order generation. Placeholder."""
    return {"message": "Orders generated"}
