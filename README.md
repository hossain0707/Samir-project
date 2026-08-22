# CBDs — China BD Store Business Suite

A polished Windows desktop application for China BD Store (CBDS) product sourcing, inventory, shipment costing, partner expenses, and profitability management.

## Highlights

- Secure local user authentication with PBKDF2 password hashing
- Inventory and SKU management with search, add, edit, and delete workflows
- Exact landed-cost calculations based on the supplied CBDS workbook
- Proportional sourcing-cost allocation
- Retail and wholesale pricing in RMB and BDT
- Partner expense and voucher-status ledger
- Branded Excel and watermarked PDF profitability reports
- Official CBDS logo throughout the application and Windows executable
- Durable local SQLite database with WAL mode and relational constraints
- High-DPI-aware, dependency-free Windows desktop interface

## Windows installation

Download `CBDs.exe` from the newest successful **Build Windows EXE** workflow run.

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

Version 1.0 is an offline-first Windows application. Its local database is intended for one trusted Windows profile. Internet-based multi-user synchronization should be added through a separately secured API and managed PostgreSQL deployment before using the same live dataset from multiple computers.
