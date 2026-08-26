# AUREVIX — Business KPI & Metrics Catalog

## 1. Core Retail Business Metrics

| Metric Name | Formula | Calculated Value (Full Dataset) | Reconciliation Status |
| :--- | :--- | :--- | :--- |
| **Total Gross Revenue** | `SUM(total_item_value)` | **$15,843,553.24** | Exact Match (0.00 variance vs Silver) |
| **Total Product Revenue** | `SUM(item_price)` | **$13,591,643.70** | Exact Match (0.00 variance vs Silver) |
| **Total Freight Revenue** | `SUM(freight_value)` | **$2,251,909.54** | Exact Match (0.00 variance vs Silver) |
| **Total Orders** | `COUNT(DISTINCT order_id)` | **98,666 orders** | Exact Match with valid orders |
| **Total Units Sold** | `SUM(order_item_quantity)` | **112,650 units** | Exact Match (1 row = 1 unit) |
| **Average Order Value (AOV)** | `Total Gross Revenue / Total Orders` | **$160.58** | Validated |
| **Average Freight per Item** | `Total Freight Revenue / Units Sold` | **$19.99** | Validated |

---

## 2. Inactivity Proxy Definition
- **Definition:** Customers whose most recent order date is older than 180 days relative to the dataset boundary (`2018-10-17`).
- **Terminology Rule:** Labeled strictly as **"Inactivity Proxy"** (or dormancy proxy), avoiding inaccurate claims of contractual customer churn.
