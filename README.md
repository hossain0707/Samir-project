# CBDs — China BD Store Business Suite v2.0

A polished Windows desktop application for China BD Store (CBDS) product sourcing, inventory, shipment costing, partner expenses, and profitability management.

[![Download CBDs for Windows](https://img.shields.io/badge/Download-CBDs_for_Windows-0B684F?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/hossain0707/Samir-project/releases/download/latest/CBDs.exe)

Click the button above to download the newest verified `CBDs.exe`. Because this repository is private, GitHub will require an authorized account to be signed in.

## Highlights

- Secure local user authentication with PBKDF2 password hashing
- Inventory and SKU management with managed product-image uploads
- Exact landed-cost calculations based on the supplied CBDS workbook
- Proportional sourcing-cost allocation
- Retail and wholesale pricing in RMB and BDT
- Partner expense and voucher-status ledger
- Branded Excel and watermarked PDF profitability reports
- Official CBDS logo throughout the application and Windows executable
- Automatic SKU and shipment-batch code generation
- Partner investments, shared-overhead allocation, and settlement balances
- Customer delivery database and supplier quote-history/quality comparison
- Retail and wholesale sales with automatic stock deduction
- Professional watermarked wholesale/retail PDF invoices
- Multi-sheet Excel reporting for products, customers, suppliers, partners, and sales
- Administrator and partner permissions, authorized-user management, and password changes
- Transactionally consistent local database backups
- Durable local SQLite database with WAL mode and relational constraints
- Polished Windows desktop interface with all runtime dependencies bundled

## Windows installation

Click **Download CBDs for Windows** at the top of this README. GitHub Actions automatically replaces the linked file after every successful build on `main`.

Default first sign-in:

- Username: `admin`
- Password: `ChangeMe123!`

Change the default password before using the application with business data.

## Run from source

Python 3.11+ is required.

```powershell
python app.py
```

The database is stored in `%LOCALAPPDATA%\CBDs\cbds.db`.

## Build the executable locally on Windows

```powershell
python -m pip install -r requirements.txt pyinstaller
pyinstaller SamirSoft.spec --clean --noconfirm
```

The executable will be created at `dist\CBDs.exe`.

## Data model and calculation rules

For every product:

1. `Shipping RMB = weight in kg × shipping rate per kg`
2. `Allocated sourcing RMB = product purchase RMB ÷ total purchase RMB × total sourcing RMB`
3. `Landed RMB = purchase RMB + shipping RMB + allocated sourcing RMB`
4. `Landed BDT = landed RMB × RMB exchange rate`
5. Retail and wholesale prices apply their configured margins to landed BDT.

## Security note

Version 2.0 is an offline-first Windows application. Its local database is intended for one trusted Windows profile. Internet-based multi-user synchronization should be added through a separately secured API and managed PostgreSQL deployment before using the same live dataset from multiple computers.
