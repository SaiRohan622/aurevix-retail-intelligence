# AUREVIX — Data Quality Firewall Rules Catalog

| Rule ID | Entity | Rule Description | Severity | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **DQ001** | Orders / Items / Reviews / Sellers | Primary / Mandatory Key Not Null | Critical | Quarantine record |
| **DQ002** | Orders / Customers | Customer Identifier Not Null | Critical | Quarantine record |
| **DQ003** | Order Items / Products | Product Identifier Not Null | Critical | Quarantine record |
| **DQ004** | Order Items / Payments / Products / Geo | Non-Negative Numerics & Coordinate Bounds | Error | Quarantine record |
| **DQ005** | Order Items | Freight value >= 0.00 | Error | Quarantine record |
| **DQ006** | Order Items / Payments | Sequence IDs / Installments >= 0 | Error | Quarantine record |
| **DQ007** | Orders | Order status in valid domain | Error | Quarantine record |
| **DQ008** | Orders | Purchase timestamp >= 2016-01-01 | Error | Quarantine record |
| **DQ009** | Orders | Delivery timestamp >= Purchase timestamp | Warning | Quarantine record |
| **DQ010** | Items / Payments / Reviews | Referential Integrity to Parent Orders | Critical | Quarantine record |
| **DQ011** | Customers / Sellers / Geolocation | Valid Brazilian State (27 Federation Units) | Error | Quarantine record |
| **DQ012** | Order Reviews | Review satisfaction score between 1 and 5 | Error | Quarantine record |
