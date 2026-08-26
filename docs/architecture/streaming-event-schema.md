# AUREVIX — Streaming Event Schema & Identifier Architecture

## 1. Streaming Kafka Event Definition
- **Kafka Topic:** `aurevix.retail.orders`
- **Serialization Format:** JSON (UTF-8 encoded string payload).
- **Partitioning Strategy:** Partitioned by `customer_state` or `order_id` across 3 topic partitions.

---

## 2. Event Payload Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AurevixRetailOrderEvent",
  "type": "object",
  "required": [
    "event_id",
    "event_time",
    "event_type",
    "order_id",
    "order_item_id",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
    "schema_version"
  ],
  "properties": {
    "event_id": {
      "type": "string",
      "description": "Deterministic SHA-256 idempotency hash: SHA256(order_id + ':' + order_item_id + ':' + event_time)"
    },
    "event_time": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC timestamp of event generation (e.g. '2026-08-21T15:30:00Z')"
    },
    "event_type": {
      "type": "string",
      "enum": ["ORDER_PLACED", "ORDER_CANCELLED", "PAYMENT_APPROVED"],
      "description": "Retail transaction lifecycle event type"
    },
    "order_id": {
      "type": "string",
      "maxLength": 32,
      "description": "Unique business order ID"
    },
    "order_item_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Sequential line item number"
    },
    "customer_id": {
      "type": "string",
      "maxLength": 32,
      "description": "Customer transaction reference"
    },
    "customer_unique_id": {
      "type": "string",
      "maxLength": 32,
      "description": "Persistent customer account identifier"
    },
    "customer_city": {
      "type": "string",
      "maxLength": 64,
      "description": "Customer municipality"
    },
    "customer_state": {
      "type": "string",
      "minLength": 2,
      "maxLength": 2,
      "description": "2-letter Brazilian state code"
    },
    "product_id": {
      "type": "string",
      "maxLength": 32,
      "description": "Product SKU reference"
    },
    "product_category": {
      "type": "string",
      "description": "English category classification"
    },
    "seller_id": {
      "type": "string",
      "maxLength": 32,
      "description": "Merchant ID"
    },
    "quantity": {
      "type": "integer",
      "minimum": 1,
      "description": "Units ordered"
    },
    "unit_price": {
      "type": "number",
      "minimum": 0.0,
      "description": "Unit price in BRL"
    },
    "freight_value": {
      "type": "number",
      "minimum": 0.0,
      "description": "Shipping cost in BRL"
    },
    "total_amount": {
      "type": "number",
      "minimum": 0.0,
      "description": "(unit_price * quantity) + freight_value"
    },
    "source": {
      "type": "string",
      "description": "Origin simulator tag ('aurevix-order-simulator')"
    },
    "schema_version": {
      "type": "string",
      "description": "Semantic schema version ('1.0.0')"
    }
  }
}
```

---

## 3. Deterministic Identifier & Idempotency Architecture

### 1. `event_id` Design
`event_id` is generated deterministically via SHA-256 hashing of business keys and event timestamp:
$$	ext{event\_id} = 	ext{SHA256}(	ext{order\_id} \parallel 	ext{":"} \parallel 	ext{order\_item\_id} \parallel 	ext{":"} \parallel 	ext{event\_time})$$

### 2. Business Deduplication Key
$$	ext{Deduplication Key} = (	ext{order\_id}, 	ext{order\_item\_id})$$

### 3. Stream Deduplication & Watermarking
- **Watermark:** 10 minutes on `event_time`.
- Spark Structured Streaming deduplicates events using `dropDuplicates(["order_id", "order_item_id"])` within the active watermark window.
- Duplicate arrivals with identical business keys within the watermark window are dropped without state corruption.
- Late-arriving events within 10 minutes are processed; arrivals exceeding 10 minutes are routed to the late-events quarantine sink.
