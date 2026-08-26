# AUREVIX — Power BI Executive Retail Analytics Specification

## 1. Report Architecture (7 Dedicated Analytical Views)

1. **Page 1 — Executive Overview:** Macro KPIs (Revenue $15.84M, Orders 98.7K, Units 112.7K, AOV $160.58), monthly revenue trajectory, category share, regional state map.
2. **Page 2 — Sales Intelligence:** MoM growth trends, price distribution, basket analysis, item price vs freight breakdown.
3. **Page 3 — Customer Intelligence:** Customer value distribution, repeat customer rate, RFM-style segmentation tiers.
4. **Page 4 — Product & Category:** Category revenue matrices, SKU performance rankings, volumetric analysis.
5. **Page 5 — Regional Intelligence:** State-level volume rankings (SP, RJ, MG), freight efficiency, inter-state logistics latency.
6. **Page 6 — Real-Time Operations:** Streaming order throughput, Kafka event rates, Spark micro-batch processing metrics.
7. **Page 7 — Data Platform Health:** SLA latency tiers (GREEN / YELLOW / RED), pipeline audit trail, Silver quarantine monitoring.

## 2. UI / UX Design System
- **Theme:** Enterprise Slate Dark Theme (`#0F172A` canvas, `#1E293B` containers, `#3B82F6` primary accent, `#10B981` positive growth).
- **Navigation & Slicers:** Global Date Range slicer, Region/State selector, Category selector.
