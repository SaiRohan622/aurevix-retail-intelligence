# AUREVIX — Source Data Inventory

This document defines the 9 source tables from the Olist Brazilian E-Commerce dataset utilized across the AUREVIX platform.

---

## 1. `olist_orders_dataset`
- **Business Purpose:** Central transaction header tracking lifecycle progression from order creation to final delivery.
- **Primary / Business Key:** `order_id`
- **Foreign Keys:** `customer_id` -> `olist_customers_dataset.customer_id`
- **Columns & Data Types:**
  - `order_id` (VARCHAR(32)): Unique order identifier.
  - `customer_id` (VARCHAR(32)): Foreign key identifying customer transaction entity.
  - `order_status` (VARCHAR(20)): Status (`delivered`, `shipped`, `canceled`, `invoiced`, `processing`, `created`, `approved`, `unavailable`).
  - `order_purchase_timestamp` (TIMESTAMP): Order timestamp in UTC.
  - `order_approved_at` (TIMESTAMP): Payment approval timestamp.
  - `order_delivered_carrier_date` (TIMESTAMP): Hand-off to shipping carrier.
  - `order_delivered_customer_date` (TIMESTAMP): Actual delivery to consumer.
  - `order_estimated_delivery_date` (TIMESTAMP): Target SLA delivery date.
- **Timestamp Attributes:** `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`.
- **Potential Quality Issues:** Missing `order_approved_at` for canceled orders, deliveries occurring after estimated date, inconsistent timestamp formats.

---

## 2. `olist_order_items_dataset`
- **Business Purpose:** Granular line-item breakdown representing individual products purchased per order.
- **Primary / Business Key:** Composite: (`order_id`, `order_item_id`)
- **Foreign Keys:**
  - `order_id` -> `olist_orders_dataset.order_id`
  - `product_id` -> `olist_products_dataset.product_id`
  - `seller_id` -> `olist_sellers_dataset.seller_id`
- **Columns & Data Types:**
  - `order_id` (VARCHAR(32)): Order reference.
  - `order_item_id` (INTEGER): Sequential item index within the order (1, 2, 3...).
  - `product_id` (VARCHAR(32)): Product SKU reference.
  - `seller_id` (VARCHAR(32)): Merchant reference.
  - `shipping_limit_date` (TIMESTAMP): Seller ship deadline.
  - `price` (DECIMAL(10,2)): Unit price of the item in BRL.
  - `freight_value` (DECIMAL(10,2)): Shipping/freight charge in BRL.
- **Potential Quality Issues:** Non-positive prices or negative freight values, orphaned product IDs.

---

## 3. `olist_products_dataset`
- **Business Purpose:** Catalog of physical and categorized goods sold across the platform.
- **Primary / Business Key:** `product_id`
- **Foreign Keys:** `product_category_name` -> `product_category_name_translation.product_category_name`
- **Columns & Data Types:**
  - `product_id` (VARCHAR(32)): Unique product SKU.
  - `product_category_name` (VARCHAR(64)): Category name in Portuguese.
  - `product_name_lenght` (INTEGER): Character length of product title.
  - `product_description_lenght` (INTEGER): Character length of description.
  - `product_photos_qty` (INTEGER): Number of catalog images.
  - `product_weight_g` (INTEGER): Weight in grams.
  - `product_length_cm`, `product_height_cm`, `product_width_cm` (INTEGER): Dimensions.
- **Potential Quality Issues:** Null category names (~610 items), misspelled column headers (`product_name_lenght` in source).

---

## 4. `olist_customers_dataset`
- **Business Purpose:** Customer identity registry and geographical residency information.
- **Primary / Business Key:** `customer_id` (Transaction-level key); `customer_unique_id` (Unique human/account key).
- **Foreign Keys:** `customer_zip_code_prefix` -> `olist_geolocation_dataset.geolocation_zip_code_prefix`
- **Columns & Data Types:**
  - `customer_id` (VARCHAR(32)): Unique per order.
  - `customer_unique_id` (VARCHAR(32)): Unique persistent customer identifier.
  - `customer_zip_code_prefix` (VARCHAR(5)): 5-digit postal code.
  - `customer_city` (VARCHAR(64)): City name.
  - `customer_state` (VARCHAR(2)): 2-letter Brazilian state code (e.g., SP, RJ).
- **Potential Quality Issues:** Multiple zip code variations per city, special characters/accents in city names.

---

## 5. `olist_order_payments_dataset`
- **Business Purpose:** Financial payment records, tender types, and installment breakdown.
- **Primary / Business Key:** Composite: (`order_id`, `payment_sequential`)
- **Foreign Keys:** `order_id` -> `olist_orders_dataset.order_id`
- **Columns & Data Types:**
  - `order_id` (VARCHAR(32)): Order identifier.
  - `payment_sequential` (INTEGER): Sequence number for split tender.
  - `payment_type` (VARCHAR(20)): Method (`credit_card`, `boleto`, `voucher`, `debit_card`, `not_defined`).
  - `payment_installments` (INTEGER): Number of installments chosen.
  - `payment_value` (DECIMAL(10,2)): Total monetary value paid in BRL.
- **Potential Quality Issues:** Split payment values differing from total order line items plus freight, `not_defined` payment types.

---

## 6. `olist_order_reviews_dataset`
- **Business Purpose:** Post-purchase customer review scores, survey comments, and satisfaction metrics.
- **Primary / Business Key:** `review_id`
- **Foreign Keys:** `order_id` -> `olist_orders_dataset.order_id`
- **Columns & Data Types:**
  - `review_id` (VARCHAR(32)): Unique review record.
  - `order_id` (VARCHAR(32)): Order referenced.
  - `review_score` (INTEGER): Rating from 1 (lowest) to 5 (highest).
  - `review_comment_title` (TEXT): Review title.
  - `review_comment_message` (TEXT): Free-text comment.
  - `review_creation_date` (TIMESTAMP): Survey sent date.
  - `review_answer_timestamp` (TIMESTAMP): Survey response timestamp.
- **Potential Quality Issues:** Multiple reviews per order, multiline raw text containing unescaped newline characters.

---

## 7. `olist_sellers_dataset`
- **Business Purpose:** Registry of marketplace merchants, origin fulfillment hubs, and regional distribution.
- **Primary / Business Key:** `seller_id`
- **Foreign Keys:** `seller_zip_code_prefix` -> `olist_geolocation_dataset.geolocation_zip_code_prefix`
- **Columns & Data Types:**
  - `seller_id` (VARCHAR(32)): Unique merchant ID.
  - `seller_zip_code_prefix` (VARCHAR(5)): 5-digit postal code.
  - `seller_city` (VARCHAR(64)): Merchant city.
  - `seller_state` (VARCHAR(2)): 2-letter state abbreviation.
- **Potential Quality Issues:** Formatting inconsistencies in city names with diacritics.

---

## 8. `olist_geolocation_dataset`
- **Business Purpose:** Geospatial mapping of Brazilian postal code prefixes to coordinates and standardized municipality names.
- **Primary / Business Key:** Composite: (`geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`)
- **Columns & Data Types:**
  - `geolocation_zip_code_prefix` (VARCHAR(5)): Postal code prefix.
  - `geolocation_lat` (DECIMAL(10,8)): Latitude coordinate.
  - `geolocation_lng` (DECIMAL(11,8)): Longitude coordinate.
  - `geolocation_city` (VARCHAR(64)): City name.
  - `geolocation_state` (VARCHAR(2)): Brazilian state code.
- **Potential Quality Issues:** High duplication rate (~1M rows for ~19k zip codes), outlier coordinates outside Brazil's geographic bounding box.

---

## 9. `product_category_name_translation`
- **Business Purpose:** Taxonomy lookup translating Portuguese category labels into standardized English.
- **Primary / Business Key:** `product_category_name`
- **Columns & Data Types:**
  - `product_category_name` (VARCHAR(64)): Category name in Portuguese.
  - `product_category_name_english` (VARCHAR(64)): Translated category name in English.
- **Potential Quality Issues:** Missing translations for newly introduced or niche categories.
