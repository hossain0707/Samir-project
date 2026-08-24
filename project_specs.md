# China BD Store — CBDs v2.0 Specification

## Platform and objective

CBDs is an offline-first Windows desktop business-management application built in Python. It preserves the supplied China BD Store workbook rules while adding structured inventory, sourcing, shipment, partner settlement, customer, supplier, sales, invoicing, reporting, authentication, and backup capabilities. A secured API can be connected in a later online phase without changing the core calculations.

## Core calculation rules

- Manual RMB-to-BDT exchange rate controls all converted values.
- Shipment RMB = product weight in kilograms × batch shipment rate per kilogram.
- Sourcing cost is allocated by each product's share of total purchase value.
- Landed cost = purchase + shipment + allocated sourcing.
- Retail and wholesale prices use independently configurable profit margins.
- Batch code = sanitized four-character company prefix + supply date (`CBDS-YYYYMMDD`).
- Suggested SKU = rounded weight + first alphabetic variant letter + rounded retail BDT price.

## Modules

1. Dashboard and inventory alerts
2. Product and SKU management, including managed image uploads and batch assignment
3. Shipment batches plus batch-specific purchasing, sourcing and overhead expenses
4. Partner investments and equal-share overhead settlement
5. Customer and delivery database
6. Supplier quote history and quality database
7. Retail/wholesale sales, stock deduction and branded PDF invoicing
8. Profitability and periodic reporting with CBDS branding/watermark
9. Admin/partner role permissions, password management and local backup

## Security and deployment

- PBKDF2-HMAC-SHA256 password hashing with per-user salts
- SQLite foreign keys, constraints, WAL mode and transactional backup
- Admin-only destructive/configuration actions
- Offline data under `%LOCALAPPDATA%\CBDs`
- Packaged as `CBDs.exe` by the verified Windows CI workflow

## Online phase boundary

True simultaneous internet access requires a separately deployed authenticated API, managed relational database, TLS, object storage and server-side authorization. The Windows v2.0 build is offline-first and preserves an online-ready relational schema; it does not claim cloud synchronization until that backend is deployed.
