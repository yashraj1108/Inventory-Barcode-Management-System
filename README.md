# Whistle — Inventory Barcode Management System

A warehouse inventory app built entirely in **Python (Flask)**: generate a
scannable barcode for every SKU, scan it with a phone or webcam to record
stock in/out, and watch inventory value and low-stock alerts update live.

## Features

- **Product catalog** — add SKUs with category, unit price, reorder
  threshold, and shelf location (aisle + bin).
- **Automatic barcode generation** — every product gets a Code128 barcode
  (via `python-barcode`) rendered as a PNG the moment it's created.
- **Camera-based scanning** — the `/scan` page uses the device camera
  (`html5-qrcode`, configured for Code128/EAN/UPC/QR) to look up a product
  instantly, with a manual SKU-entry fallback.
- **Stock in / stock out logging** — every scan or manual adjustment is
  recorded as a `Transaction`, so nothing changes stock without a paper trail.
- **Low-stock alerts** — products at or below their reorder threshold are
  flagged across the dashboard and product list.
- **Stock heatmap** — a warehouse-location grid, color-coded by how close
  each shelf is to running out, so problem areas are visible at a glance.
- **Purchase/transaction history** — a filterable log of every stock
  movement, plus a full history on each product's own page.
- **Supplier directory** — track who each product is sourced from.

## Tech stack

| Layer      | Choice                                             |
|------------|-----------------------------------------------------|
| Backend    | Flask, Flask-SQLAlchemy                             |
| Database   | SQLite (swap the URI for Postgres/MySQL in production) |
| Barcodes   | `python-barcode` (generation) + `html5-qrcode` CDN (browser-side scanning) |
| Frontend   | Server-rendered Jinja templates, vanilla JS, no build step |

## Project structure

```
inventory-barcode-system/
├── app.py                  # Flask app factory + all routes
├── config.py                # App configuration
├── models.py                  # Supplier, Product, Transaction models
├── barcode_utils.py             # Barcode PNG generation
├── requirements.txt
├── static/
│   ├── css/style.css          # Design system
│   └── barcodes/                # Generated barcode PNGs (gitignored)
└── templates/
    ├── base.html
    ├── dashboard.html            # Stats + stock heatmap
    ├── products.html               # Searchable product list
    ├── product_new.html              # Add-product form
    ├── product_detail.html             # Barcode + stock adjustment
    ├── scan.html                        # Camera scanner
    ├── history.html                       # Transaction log
    └── suppliers.html                       # Supplier directory
```

## Getting started

```bash
# 1. Clone and enter the project
git clone https://github.com/<your-username>/inventory-barcode-system.git
cd inventory-barcode-system

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

The app starts at **http://localhost:5001**. On first run it creates a local
SQLite database at `instance/warehouse.db` automatically.

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | Stats, stock heatmap, low-stock alerts, recent activity |
| Products | `/products` | Searchable product list |
| Add product | `/products/new` | Create a SKU and generate its barcode |
| Product detail | `/products/<id>` | Barcode image, details, stock adjustment |
| Scanner | `/scan` | Camera-based barcode lookup + stock in/out |
| History | `/history` | Full transaction log, filterable by type |
| Suppliers | `/suppliers` | Supplier directory |

> The camera scanner needs HTTPS or `localhost` to access the device camera —
> a browser security requirement. It works out of the box on `localhost` and
> on any deployed host served over HTTPS.

## API reference

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `POST` | `/api/lookup` | `{"barcode": "<sku>"}` | Product details, or `not_found` |
| `POST` | `/api/transaction` | `{"barcode", "type": "IN"\|"OUT", "quantity", "note"}` | Updated product + transaction record |
| `GET` | `/api/stats` | — | `{total_skus, total_value, low_stock, today_transactions}` |

## Configuration

Environment variables (all optional, sensible defaults are used otherwise):

| Variable | Default | Description |
|----------|---------|--------------|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask session secret — **set this in production** |
| `DATABASE_URL` | local SQLite file | Any SQLAlchemy-compatible connection string |
| `COMPANY_NAME` | `Whistle Warehouse` | Name shown across the UI |

## Roadmap / ideas for extension

- CSV import/export for bulk product uploads
- Purchase orders that auto-generate when a SKU crosses its reorder threshold
- Multi-warehouse support (locations scoped to a warehouse, not just aisle/bin)
- Organizer login so `/scan` and product management aren't publicly accessible

## License

MIT — use it, fork it, adapt it for your own warehouse.
