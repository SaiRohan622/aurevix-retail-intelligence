# AUREVIX — Dashboard Metrics & Business Formulas

| Metric | Source Table | Formula / Logic | Validated Value |
| :--- | :--- | :--- | :--- |
| **Total Gross Revenue** | `gold.fact_sales` | `SUM(total_item_value)` | **$15,843,553.24** |
| **Total Orders** | `gold.fact_sales` | `COUNT(DISTINCT order_id)` | **98,666** |
| **Total Units Sold** | `gold.fact_sales` | `COUNT(order_item_id)` | **112,650** |
| **Average Order Value (AOV)** | `gold.fact_sales` | `SUM(total_item_value) / COUNT(DISTINCT order_id)` | **$160.58** |
| **Average Logistics Freight** | `gold.fact_sales` | `SUM(freight_value) / COUNT(order_item_id)` | **$19.99** |
| **Unique Customers** | `gold.dim_customer` | `COUNT(DISTINCT customer_unique_id)` | **96,096** |
