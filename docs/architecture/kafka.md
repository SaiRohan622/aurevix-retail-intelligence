# AUREVIX — Apache Kafka Specification

## 1. Topic Architecture & Configuration

| Parameter | Configuration Value | Description |
| :--- | :--- | :--- |
| **Topic Name** | `aurevix.retail.order-events` | Main streaming ingestion topic for order-item events |
| **Partitions** | `1` (Development / Local) | Single partition for local single-broker Docker container |
| **Replication Factor** | `1` | Single broker cluster deployment |
| **Serialization** | `JSON (UTF-8)` | Structured retail event payloads |
| **Key Strategy** | `order_id` (String) | Partition affinity by order identifier |
| **Retention Policy** | `168 hours` (7 days) | Temporary retention window for streaming consumer recovery |

---

## 2. Event Contract Specification
```json
{
  "event_id": "9a6df790757a3e74b882195f269a8421867c469b8214371987d60ff3be2b6531",
  "event_type": "ORDER_ITEM_CREATED",
  "event_timestamp": "2018-05-01 10:00:00",
  "order_id": "e481f51cbdc54678b7cc49136f2d6af7",
  "order_item_id": 1,
  "customer_id": "9ef432eb6251297304e76186b10a928d",
  "product_id": "87c37892c33e414cd93b25e3e6ba36f5",
  "seller_id": "3504c0c9712944fd9e31ae0ff609a5f0",
  "price": 29.99,
  "freight_value": 8.72,
  "quantity": 1,
  "order_status": "delivered",
  "source": "olist_replay",
  "schema_version": "1.0"
}
```
