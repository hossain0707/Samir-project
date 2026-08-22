from __future__ import annotations

import csv
import hashlib
import json
import os
import secrets
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk


APP_NAME = "CBDs"
APP_VERSION = "1.0.1"
DEFAULT_FONT = "{Segoe UI} 10"
BG = "#F4F7FB"
CARD = "#FFFFFF"
INK = "#172033"
MUTED = "#6B7280"
NAV = "#101A2F"
PRIMARY = "#6C4CF1"
PRIMARY_DARK = "#5535DC"
GREEN = "#0FA968"
ORANGE = "#F59E0B"
RED = "#E6465C"
BORDER = "#E5EAF2"


def app_data_dir() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", Path.home())) / "CBDs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def money(value: float, currency: str = "BDT") -> str:
    symbol = "৳" if currency == "BDT" else "¥"
    return f"{symbol}{value:,.2f}"


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return salt.hex(), digest.hex()


class Database:
    def __init__(self) -> None:
        self.path = app_data_dir() / "cbds.db"
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()
        self._seed()

    def _migrate(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings(
          key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('admin','partner')),
          salt TEXT NOT NULL, password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
          category TEXT NOT NULL, name TEXT NOT NULL, size TEXT, variant TEXT,
          quantity INTEGER NOT NULL CHECK(quantity >= 0), weight_g REAL NOT NULL CHECK(weight_g >= 0),
          shipping_rate_kg REAL NOT NULL CHECK(shipping_rate_kg >= 0), purchase_rmb REAL NOT NULL CHECK(purchase_rmb >= 0),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS expenses(
          id INTEGER PRIMARY KEY AUTOINCREMENT, expense_date TEXT NOT NULL,
          supplier TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL,
          quantity INTEGER NOT NULL DEFAULT 1, amount_rmb REAL NOT NULL DEFAULT 0,
          paid_by TEXT NOT NULL, voucher_status TEXT NOT NULL DEFAULT 'Pending', notes TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        defaults = {
            "rmb_rate": "19.2", "retail_margin": "30", "wholesale_margin": "20",
            "sourcing_cost_rmb": "277.56", "company_prefix": "CBDS", "supply_date": "2026-08-01"
        }
        self.conn.executemany("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", defaults.items())
        self.conn.commit()

    def _seed(self) -> None:
        if not self.conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            salt, digest = hash_password("ChangeMe123!")
            self.conn.execute(
                "INSERT INTO users(name,username,role,salt,password_hash) VALUES(?,?,?,?,?)",
                ("Main Administrator", "admin", "admin", salt, digest),
            )
        if not self.conn.execute("SELECT 1 FROM products LIMIT 1").fetchone():
            path = resource_path("sample_data.json")
            if path.exists():
                rows = json.loads(path.read_text(encoding="utf-8"))["products"]
                self.conn.executemany(
                    "INSERT INTO products(code,category,name,size,variant,quantity,weight_g,shipping_rate_kg,purchase_rmb) VALUES(:code,:category,:name,:size,:variant,:quantity,:weight_g,:shipping_rate_kg,:purchase_rmb)", rows
                )
        if not self.conn.execute("SELECT 1 FROM expenses LIMIT 1").fetchone():
            expenses = [
                ("2026-08-11", "Beijing to Baigo", "Transportation", "High-speed road fees", 2, 77.56, "Flower", "Submitted"),
                ("2026-08-01", "Warehouse", "Logistics", "Estimated warehouse delivery", 1, 200, "Flower", "Pending"),
            ]
            self.conn.executemany("INSERT INTO expenses(expense_date,supplier,category,description,quantity,amount_rmb,paid_by,voucher_status) VALUES(?,?,?,?,?,?,?,?)", expenses)
        self.conn.commit()

    def setting(self, key: str) -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else ""

    def set_settings(self, values: dict[str, str]) -> None:
        self.conn.executemany("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", values.items())
        self.conn.commit()

    def authenticate(self, username: str, password: str):
        row = self.conn.execute("SELECT * FROM users WHERE lower(username)=lower(?) AND active=1", (username.strip(),)).fetchone()
        if not row:
            return None
        _, digest = hash_password(password, bytes.fromhex(row["salt"]))
        return row if secrets.compare_digest(digest, row["password_hash"]) else None

    def products(self, query: str = ""):
        term = f"%{query.strip()}%"
        return self.conn.execute("SELECT * FROM products WHERE code LIKE ? OR name LIKE ? OR category LIKE ? OR variant LIKE ? ORDER BY id", (term, term, term, term)).fetchall()

    def expenses(self):
        return self.conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC,id DESC").fetchall()

    def save_product(self, values: tuple, product_id: int | None = None) -> None:
        if product_id:
            self.conn.execute("UPDATE products SET code=?,category=?,name=?,size=?,variant=?,quantity=?,weight_g=?,shipping_rate_kg=?,purchase_rmb=? WHERE id=?", values + (product_id,))
        else:
            self.conn.execute("INSERT INTO products(code,category,name,size,variant,quantity,weight_g,shipping_rate_kg,purchase_rmb) VALUES(?,?,?,?,?,?,?,?,?)", values)
        self.conn.commit()

    def delete_product(self, product_id: int) -> None:
        self.conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        self.conn.commit()

    def save_expense(self, values: tuple) -> None:
        self.conn.execute("INSERT INTO expenses(expense_date,supplier,category,description,quantity,amount_rmb,paid_by,voucher_status,notes) VALUES(?,?,?,?,?,?,?,?,?)", values)
        self.conn.commit()


@dataclass(frozen=True)
class Costing:
    purchase_rmb: float
    shipping_rmb: float
    sourcing_rmb: float
    total_rmb: float
    total_bdt: float
    retail_bdt: float
    wholesale_bdt: float


def calculate_cost(product, total_purchase_rmb: float, sourcing_rmb: float, rate: float, retail: float, wholesale: float) -> Costing:
    purchase = float(product["purchase_rmb"])
    shipping = float(product["weight_g"]) / 1000 * float(product["shipping_rate_kg"])
    allocated = (purchase / total_purchase_rmb * sourcing_rmb) if total_purchase_rmb else 0
    total = purchase + shipping + allocated
    return Costing(purchase, shipping, allocated, total, total * rate, total * rate * (1 + retail / 100), total * rate * (1 + wholesale / 100))


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.db = Database()
        self.user = None
        self.title(APP_NAME)
        self.geometry("1440x880")
        self.minsize(1120, 720)
        self.configure(bg=BG)
        try:
            self.iconbitmap(resource_path("assets/cbds.ico"))
        except tk.TclError:
            pass
        # Braces keep the multi-word Windows font family together. Without
        # them Tk parses "UI" as the point size and raises a TclError.
        self.option_add("*Font", DEFAULT_FONT)
        self._styles()
        self.show_login()

    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK, rowheight=38, borderwidth=0)
        s.configure("Treeview.Heading", background="#EEF1F7", foreground=MUTED, font=("Segoe UI Semibold", 9), relief="flat", padding=8)
        s.map("Treeview", background=[("selected", "#EDE9FE")], foreground=[("selected", INK)])
        s.configure("TEntry", padding=8, fieldbackground=CARD)
        s.configure("TCombobox", padding=7, fieldbackground=CARD)

    def logo_image(self, size: tuple[int, int]):
        image = Image.open(resource_path("assets/cbds_logo.png")).convert("RGBA")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def show_login(self):
        self.clear()
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        left = tk.Frame(shell, bg=NAV, width=560)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self.login_logo = self.logo_image((315, 155))
        tk.Label(left, image=self.login_logo, bg="white", bd=0).pack(anchor="w", padx=64, pady=(70, 0))
        tk.Label(left, text="Business clarity,\nfrom source to sale.", fg="white", bg=NAV, justify="left", font=("Segoe UI Semibold", 33)).pack(anchor="w", padx=64, pady=(90, 25))
        tk.Label(left, text="Inventory • Import costing • Partner ledger\nBuilt for China BD Store", fg="#AEB8CC", bg=NAV, justify="left", font=("Segoe UI", 12)).pack(anchor="w", padx=64)
        panel = tk.Frame(shell, bg=BG)
        panel.pack(side="left", fill="both", expand=True)
        form = tk.Frame(panel, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        form.place(relx=.5, rely=.5, anchor="center", width=440, height=500)
        tk.Label(form, text="Welcome back", fg=INK, bg=CARD, font=("Segoe UI Semibold", 25)).pack(anchor="w", padx=50, pady=(50, 8))
        tk.Label(form, text="Sign in to continue to CBDS Workspace", fg=MUTED, bg=CARD).pack(anchor="w", padx=50, pady=(0, 34))
        tk.Label(form, text="Username", fg=INK, bg=CARD, font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=50)
        user = ttk.Entry(form)
        user.pack(fill="x", padx=50, pady=(7, 19))
        user.insert(0, "admin")
        tk.Label(form, text="Password", fg=INK, bg=CARD, font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=50)
        pwd_row = tk.Frame(form, bg=CARD)
        pwd_row.pack(fill="x", padx=50, pady=(7, 11))
        pwd = ttk.Entry(pwd_row, show="●")
        pwd.pack(side="left", fill="x", expand=True)
        show = tk.BooleanVar()
        tk.Checkbutton(pwd_row, text="Show", variable=show, command=lambda: pwd.configure(show="" if show.get() else "●"), bg=CARD, fg=MUTED, activebackground=CARD, bd=0).pack(side="left", padx=(8, 0))
        remember = tk.BooleanVar(value=True)
        tk.Checkbutton(form, text="Remember my username", variable=remember, bg=CARD, fg=MUTED, activebackground=CARD, bd=0).pack(anchor="w", padx=46)
        status = tk.Label(form, text="", fg=RED, bg=CARD)
        status.pack(pady=(6, 0))
        def login(*_):
            row = self.db.authenticate(user.get(), pwd.get())
            if not row:
                status.configure(text="Incorrect username or password")
                return
            self.user = row
            self.show_workspace()
        self.action_button(form, "Sign in securely", login).pack(fill="x", padx=50, pady=(12, 12))
        tk.Label(form, text="First sign-in: admin / ChangeMe123!", fg=MUTED, bg=CARD, font=("Segoe UI", 9)).pack()
        pwd.bind("<Return>", login)
        pwd.focus_set()

    def show_workspace(self):
        self.clear()
        sidebar = tk.Frame(self, bg=NAV, width=236)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar_logo = self.logo_image((174, 88))
        tk.Label(sidebar, image=self.sidebar_logo, bg="white", bd=0).pack(anchor="w", padx=27, pady=(24, 7))
        tk.Label(sidebar, text="CBDS Business Suite", fg="#8290AA", bg=NAV, font=("Segoe UI", 9)).pack(anchor="w", padx=27, pady=(0, 24))
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        links = [("▦", "Dashboard", self.dashboard), ("▣", "Inventory", self.inventory), ("↗", "Purchasing & expenses", self.expenses), ("◫", "Profitability report", self.reports), ("⚙", "Settings", self.settings)]
        self.nav_buttons = []
        for icon, label, command in links:
            b = tk.Button(sidebar, text=f"  {icon}   {label}", command=lambda c=command, x=label: self.navigate(c, x), bg=NAV, fg="#C7D0E0", activebackground="#1F2A44", activeforeground="white", relief="flat", bd=0, anchor="w", padx=20, pady=13, font=("Segoe UI Semibold", 10), cursor="hand2")
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons.append((label, b))
        tk.Frame(sidebar, bg=NAV).pack(fill="both", expand=True)
        tk.Label(sidebar, text=self.user["name"], fg="white", bg=NAV, font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=27)
        tk.Label(sidebar, text=self.user["role"].title(), fg="#8290AA", bg=NAV, font=("Segoe UI", 9)).pack(anchor="w", padx=27, pady=(2, 8))
        tk.Button(sidebar, text="Sign out", command=self.show_login, fg="#B9A7FF", bg=NAV, activebackground=NAV, relief="flat", bd=0, anchor="w", padx=23).pack(fill="x", pady=(0, 24))
        self.navigate(self.dashboard, "Dashboard")

    def navigate(self, command, name):
        for label, b in self.nav_buttons:
            b.configure(bg="#241F4F" if label == name else NAV, fg="white" if label == name else "#C7D0E0")
        command()

    def page(self, title: str, subtitle: str):
        for w in self.content.winfo_children():
            w.destroy()
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", padx=34, pady=(27, 20))
        tk.Label(header, text=title, bg=BG, fg=INK, font=("Segoe UI Semibold", 24)).pack(anchor="w")
        tk.Label(header, text=subtitle, bg=BG, fg=MUTED).pack(anchor="w", pady=(4, 0))
        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        return body

    def action_button(self, parent, text, command, secondary=False):
        return tk.Button(parent, text=text, command=command, bg=CARD if secondary else PRIMARY, fg=INK if secondary else "white", activebackground="#F7F7FB" if secondary else PRIMARY_DARK, activeforeground=INK if secondary else "white", relief="flat", bd=0, padx=18, pady=10, cursor="hand2", font=("Segoe UI Semibold", 10), highlightthickness=1 if secondary else 0, highlightbackground=BORDER)

    def card(self, parent):
        return tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)

    def context(self):
        products = self.db.products()
        rate = float(self.db.setting("rmb_rate"))
        retail = float(self.db.setting("retail_margin"))
        wholesale = float(self.db.setting("wholesale_margin"))
        sourcing = float(self.db.setting("sourcing_cost_rmb"))
        purchase = sum(float(p["purchase_rmb"]) for p in products)
        costs = [calculate_cost(p, purchase, sourcing, rate, retail, wholesale) for p in products]
        return products, costs, rate, retail, wholesale, sourcing

    def dashboard(self):
        body = self.page("Good day, Hossain", "Here is the current sourcing and inventory position.")
        products, costs, rate, _, _, _ = self.context()
        metrics = [
            ("Inventory units", str(sum(p["quantity"] for p in products)), "Across all active products", PRIMARY),
            ("Landed inventory cost", money(sum(c.total_bdt * p["quantity"] for c, p in zip(costs, products))), f"At {rate:g} BDT / RMB", GREEN),
            ("Projected retail value", money(sum(c.retail_bdt * p["quantity"] for c, p in zip(costs, products))), "Current retail margin", ORANGE),
            ("Low-stock products", str(sum(1 for p in products if p["quantity"] <= 2)), "Needs attention", RED),
        ]
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x")
        for label, value, hint, color in metrics:
            c = self.card(row); c.pack(side="left", fill="x", expand=True, padx=(0, 14))
            tk.Frame(c, bg=color, height=4).pack(fill="x")
            tk.Label(c, text=label, bg=CARD, fg=MUTED, font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=20, pady=(18, 7))
            tk.Label(c, text=value, bg=CARD, fg=INK, font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=20)
            tk.Label(c, text=hint, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(5, 18))
        lower = tk.Frame(body, bg=BG); lower.pack(fill="both", expand=True, pady=(22, 0))
        table_card = self.card(lower); table_card.pack(side="left", fill="both", expand=True, padx=(0, 18))
        tk.Label(table_card, text="Inventory highlights", bg=CARD, fg=INK, font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=20, pady=(18, 3))
        tk.Label(table_card, text="Highest projected retail value", bg=CARD, fg=MUTED).pack(anchor="w", padx=20, pady=(0, 13))
        tree = ttk.Treeview(table_card, columns=("name","stock","cost","retail"), show="headings", height=10)
        for col, label, width in [("name","Product",260),("stock","Stock",70),("cost","Landed",110),("retail","Retail",110)]: tree.heading(col,text=label); tree.column(col,width=width,anchor="e" if col != "name" else "w")
        ranked = sorted(zip(products,costs), key=lambda x:x[1].retail_bdt*x[0]["quantity"], reverse=True)[:10]
        for p,cost in ranked: tree.insert("", "end", values=(p["name"],p["quantity"],money(cost.total_bdt),money(cost.retail_bdt)))
        tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        side = self.card(lower); side.pack(side="left", fill="y", ipadx=8)
        tk.Label(side, text="Supply batch", bg=CARD, fg=INK, font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=20, pady=(18, 20))
        prefix = self.db.setting("company_prefix")[-4:].upper(); supply = self.db.setting("supply_date")
        for label,value in [("Supply code", f"{prefix}-{supply.replace('-','')}"),("Supply date",supply),("Exchange rate",f"1 RMB = {rate:g} BDT"),("Active SKUs",str(len(products)))]:
            tk.Label(side,text=label,bg=CARD,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w",padx=20)
            tk.Label(side,text=value,bg=CARD,fg=INK,font=("Segoe UI Semibold",12)).pack(anchor="w",padx=20,pady=(2,17))

    def inventory(self):
        body = self.page("Inventory", "Manage products, stock, shipment inputs, and landed cost.")
        toolbar = tk.Frame(body,bg=BG); toolbar.pack(fill="x",pady=(0,12))
        search = ttk.Entry(toolbar); search.pack(side="left",fill="x",expand=True); search.insert(0,"")
        self.action_button(toolbar,"Search",lambda:self._fill_inventory(tree,search.get()),secondary=True).pack(side="left",padx=8)
        self.action_button(toolbar,"+ Add product",lambda:self.product_dialog()).pack(side="right")
        wrap=self.card(body); wrap.pack(fill="both",expand=True)
        cols=("id","code","name","category","variant","qty","cost","retail")
        tree=ttk.Treeview(wrap,columns=cols,show="headings")
        labels=("ID","Code","Product","Category","Variant","Stock","Landed BDT","Retail BDT")
        for col,label in zip(cols,labels): tree.heading(col,text=label)
        widths=(55,110,230,100,110,70,115,115)
        for col,w in zip(cols,widths): tree.column(col,width=w,anchor="e" if col in ("qty","cost","retail") else "w")
        tree.pack(fill="both",expand=True,padx=15,pady=(15,8))
        actions=tk.Frame(wrap,bg=CARD);actions.pack(fill="x",padx=15,pady=(0,15))
        def selected_id():
            selected=tree.selection(); return int(tree.item(selected[0],"values")[0]) if selected else None
        self.action_button(actions,"Edit selected",lambda:self.product_dialog(selected_id()),secondary=True).pack(side="left")
        def delete():
            pid=selected_id()
            if pid and messagebox.askyesno("Delete product","Delete the selected product? This cannot be undone."):
                self.db.delete_product(pid); self._fill_inventory(tree,search.get())
        self.action_button(actions,"Delete",delete,secondary=True).pack(side="left",padx=8)
        search.bind("<Return>",lambda _:self._fill_inventory(tree,search.get()))
        self._fill_inventory(tree,"")

    def _fill_inventory(self, tree, query):
        tree.delete(*tree.get_children())
        products, _, rate, retail, wholesale, sourcing = self.context()
        filtered=self.db.products(query); total=sum(float(p["purchase_rmb"]) for p in products)
        for p in filtered:
            c=calculate_cost(p,total,sourcing,rate,retail,wholesale)
            tree.insert("","end",values=(p["id"],p["code"],p["name"],p["category"],p["variant"],p["quantity"],f"{c.total_bdt:,.2f}",f"{c.retail_bdt:,.2f}"))

    def product_dialog(self, product_id=None):
        row=self.db.conn.execute("SELECT * FROM products WHERE id=?",(product_id,)).fetchone() if product_id else None
        win=tk.Toplevel(self);win.title("Edit product" if row else "Add product");win.geometry("560x650");win.configure(bg=CARD);win.transient(self);win.grab_set()
        tk.Label(win,text="Edit product" if row else "New inventory product",bg=CARD,fg=INK,font=("Segoe UI Semibold",20)).pack(anchor="w",padx=32,pady=(25,18))
        form=tk.Frame(win,bg=CARD);form.pack(fill="both",expand=True,padx=32)
        fields=[("Product code","code"),("Category","category"),("Product name","name"),("Size","size"),("Variant / color","variant"),("Quantity","quantity"),("Weight (grams)","weight_g"),("Shipment rate / kg (RMB)","shipping_rate_kg"),("Purchase price / unit (RMB)","purchase_rmb")]
        entries={}
        for label,key in fields:
            tk.Label(form,text=label,bg=CARD,fg=INK,font=("Segoe UI Semibold",9)).pack(anchor="w")
            e=ttk.Entry(form);e.pack(fill="x",pady=(4,11));entries[key]=e
            if row:e.insert(0,row[key] if row[key] is not None else "")
        def save():
            try:
                values=(entries["code"].get().strip(),entries["category"].get().strip(),entries["name"].get().strip(),entries["size"].get().strip(),entries["variant"].get().strip(),int(entries["quantity"].get()),float(entries["weight_g"].get()),float(entries["shipping_rate_kg"].get()),float(entries["purchase_rmb"].get()))
                if not all(values[:3]): raise ValueError("Code, category, and name are required")
                self.db.save_product(values,product_id);win.destroy();self.inventory()
            except (ValueError,sqlite3.IntegrityError) as exc: messagebox.showerror("Cannot save",str(exc),parent=win)
        self.action_button(form,"Save product",save).pack(fill="x",pady=(5,20))

    def expenses(self):
        body=self.page("Purchasing & expenses","Record sourcing, transport, customs, and partner-paid costs.")
        top=tk.Frame(body,bg=BG);top.pack(fill="x",pady=(0,12));self.action_button(top,"+ Record expense",self.expense_dialog).pack(side="right")
        wrap=self.card(body);wrap.pack(fill="both",expand=True)
        cols=("id","date","supplier","category","description","rmb","bdt","payer","voucher")
        tree=ttk.Treeview(wrap,columns=cols,show="headings")
        for c,l in zip(cols,("ID","Date","Supplier","Category","Description","RMB","BDT","Paid by","Voucher")):tree.heading(c,text=l)
        for c,w in zip(cols,(45,95,150,115,250,85,105,90,90)):tree.column(c,width=w,anchor="e" if c in ("rmb","bdt") else "w")
        rate=float(self.db.setting("rmb_rate"))
        for e in self.db.expenses():tree.insert("","end",values=(e["id"],e["expense_date"],e["supplier"],e["category"],e["description"],f'{e["amount_rmb"]:,.2f}',f'{e["amount_rmb"]*rate:,.2f}',e["paid_by"],e["voucher_status"]))
        tree.pack(fill="both",expand=True,padx=15,pady=15)

    def expense_dialog(self):
        win=tk.Toplevel(self);win.title("Record expense");win.geometry("560x670");win.configure(bg=CARD);win.transient(self);win.grab_set()
        tk.Label(win,text="Record purchasing expense",bg=CARD,fg=INK,font=("Segoe UI Semibold",20)).pack(anchor="w",padx=32,pady=(25,18))
        form=tk.Frame(win,bg=CARD);form.pack(fill="both",expand=True,padx=32)
        specs=[("Expense date","date",date.today().isoformat()),("Supplier","supplier",""),("Category","category","Product Sourcing"),("Description","description",""),("Quantity","quantity","1"),("Amount (RMB)","amount","0"),("Paid by","paid_by","Samir"),("Voucher status","voucher","Pending"),("Notes","notes","")]
        entries={}
        for label,key,default in specs:
            tk.Label(form,text=label,bg=CARD,fg=INK,font=("Segoe UI Semibold",9)).pack(anchor="w")
            if key in ("category","voucher"):
                values=("Product Sourcing","Transportation","Local Conveyance","Customs Fees","Logistics","Other") if key=="category" else ("Pending","Submitted")
                e=ttk.Combobox(form,values=values,state="readonly");e.set(default)
            else:e=ttk.Entry(form);e.insert(0,default)
            e.pack(fill="x",pady=(4,10));entries[key]=e
        def save():
            try:
                datetime.strptime(entries["date"].get(),"%Y-%m-%d")
                vals=(entries["date"].get(),entries["supplier"].get().strip(),entries["category"].get(),entries["description"].get().strip(),int(entries["quantity"].get()),float(entries["amount"].get()),entries["paid_by"].get().strip(),entries["voucher"].get(),entries["notes"].get().strip())
                if not vals[1] or not vals[3] or not vals[6]:raise ValueError("Supplier, description, and payer are required")
                self.db.save_expense(vals);win.destroy();self.expenses()
            except ValueError as exc:messagebox.showerror("Cannot save",str(exc),parent=win)
        self.action_button(form,"Save expense",save).pack(fill="x",pady=(4,20))

    def reports(self):
        body=self.page("Profitability report","Auditable landed cost and selling-price calculations for every SKU.")
        bar=tk.Frame(body,bg=BG);bar.pack(fill="x",pady=(0,12))
        self.action_button(bar,"Export PDF",self.export_pdf,secondary=True).pack(side="right")
        self.action_button(bar,"Export Excel",self.export_xlsx,secondary=True).pack(side="right",padx=(0,8))
        wrap=self.card(body);wrap.pack(fill="both",expand=True)
        cols=("code","name","purchase","ship","allocated","landed","retail","wholesale","margin")
        tree=ttk.Treeview(wrap,columns=cols,show="headings")
        for c,l in zip(cols,("Code","Product","Purchase RMB","Ship RMB","Sourcing RMB","Landed BDT","Retail BDT","Wholesale BDT","Retail profit")):tree.heading(c,text=l)
        for c,w in zip(cols,(105,210,100,90,105,110,110,120,105)):tree.column(c,width=w,anchor="e" if c not in ("code","name") else "w")
        products,costs,_,_,_,_=self.context()
        for p,c in zip(products,costs):tree.insert("","end",values=(p["code"],p["name"],f"{c.purchase_rmb:,.2f}",f"{c.shipping_rmb:,.2f}",f"{c.sourcing_rmb:,.2f}",f"{c.total_bdt:,.2f}",f"{c.retail_bdt:,.2f}",f"{c.wholesale_bdt:,.2f}",f"{c.retail_bdt-c.total_bdt:,.2f}"))
        tree.pack(fill="both",expand=True,padx=15,pady=15)

    def report_rows(self):
        products,costs,_,_,_,_=self.context()
        return [[p["code"],p["name"],p["category"],p["quantity"],c.purchase_rmb,c.shipping_rmb,c.sourcing_rmb,c.total_bdt,c.retail_bdt,c.wholesale_bdt] for p,c in zip(products,costs)]

    def export_xlsx(self):
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",filetypes=[("Excel workbook","*.xlsx")],initialfile=f"CBDS-profitability-{date.today()}.xlsx")
        if not path:return
        try:
            from openpyxl import Workbook
            from openpyxl.drawing.image import Image as XLImage
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            wb=Workbook();ws=wb.active;ws.title="Profitability"
            ws.merge_cells("A1:J1");ws["A1"]="CHINA BD STORE — PROFITABILITY REPORT";ws["A1"].font=Font(size=18,bold=True,color="FFFFFF");ws["A1"].fill=PatternFill("solid",fgColor="0B684F");ws["A1"].alignment=Alignment(horizontal="center");ws.row_dimensions[1].height=32
            ws.merge_cells("A2:J2");ws["A2"]=f"Official CBDS report • Generated by {APP_NAME} {APP_VERSION} • {datetime.now():%Y-%m-%d %H:%M}";ws["A2"].font=Font(italic=True,color="666666");ws["A2"].alignment=Alignment(horizontal="center")
            logo=XLImage(resource_path("assets/cbds_logo.png"));logo.width=210;logo.height=105;ws.add_image(logo,"A4");ws.row_dimensions[4].height=82
            headers=["Code","Product","Category","Quantity","Purchase RMB","Shipping RMB","Sourcing RMB","Landed BDT","Retail BDT","Wholesale BDT"]
            for col,value in enumerate(headers,1):
                cell=ws.cell(6,col,value);cell.font=Font(bold=True,color="FFFFFF");cell.fill=PatternFill("solid",fgColor="B91C2D");cell.alignment=Alignment(horizontal="center")
            thin=Side(style="thin",color="E5E7EB")
            for r_idx,row in enumerate(self.report_rows(),7):
                for c_idx,value in enumerate(row,1):
                    cell=ws.cell(r_idx,c_idx,value);cell.border=Border(bottom=thin);cell.fill=PatternFill("solid",fgColor="F5FAF8" if r_idx%2 else "FFFFFF")
                    if c_idx>=4:cell.number_format='#,##0.00'
            widths=[16,30,18,12,16,16,16,16,16,18]
            for i,width in enumerate(widths,1):ws.column_dimensions[chr(64+i)].width=width
            ws.freeze_panes="A7";ws.auto_filter.ref=f"A6:J{6+len(self.report_rows())}";ws.sheet_view.showGridLines=False
            ws.oddFooter.center.text="CBDS • China BD Store • Value in Every Detail • From China to your home"
            ws.oddFooter.center.size=9;ws.oddFooter.center.color="777777"
            ws.oddHeader.right.text="CBDS"
            wb.save(path);messagebox.showinfo("Export complete",f"Branded Excel report saved to:\n{path}")
        except Exception as exc:messagebox.showerror("Export failed",str(exc))

    def export_pdf(self):
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF document","*.pdf")],initialfile=f"CBDS-profitability-{date.today()}.pdf")
        if not path:return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import Image as PDFImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
            def branded_page(canvas,doc):
                canvas.saveState();canvas.setFillAlpha(.07);canvas.drawImage(str(resource_path("assets/cbds_watermark.png")),70*mm,45*mm,width=160*mm,height=80*mm,mask="auto",preserveAspectRatio=True,anchor="c")
                canvas.setFillAlpha(1);canvas.setFont("Helvetica",8);canvas.setFillColor(colors.HexColor("#6B7280"));canvas.drawCentredString(148.5*mm,9*mm,"CBDS • China BD Store • Value in Every Detail • From China to your home");canvas.restoreState()
            doc=SimpleDocTemplate(path,pagesize=landscape(A4),rightMargin=12*mm,leftMargin=12*mm,topMargin=10*mm,bottomMargin=17*mm)
            styles=getSampleStyleSheet();story=[PDFImage(str(resource_path("assets/cbds_logo.png")),width=60*mm,height=30*mm),Paragraph("<b>Product Profitability Report</b>",styles["Title"]),Paragraph(f"Generated by {APP_NAME} {APP_VERSION} on {datetime.now():%Y-%m-%d %H:%M}",styles["Normal"]),Spacer(1,5*mm)]
            headers=["Code","Product","Category","Qty","Buy RMB","Ship RMB","Source RMB","Landed BDT","Retail BDT","Wholesale BDT"]
            data=[headers]+[[str(v) if i<4 else f"{float(v):,.2f}" for i,v in enumerate(row)] for row in self.report_rows()]
            table=Table(data,repeatRows=1,colWidths=[22*mm,43*mm,27*mm,12*mm,20*mm,20*mm,22*mm,24*mm,24*mm,27*mm])
            table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0B684F")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7.2),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#D1D5DB")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F3F8F6")]),("ALIGN",(3,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
            story.append(table);doc.build(story,onFirstPage=branded_page,onLaterPages=branded_page);messagebox.showinfo("Export complete",f"Watermarked PDF report saved to:\n{path}")
        except Exception as exc:messagebox.showerror("Export failed",str(exc))

    def settings(self):
        body=self.page("Settings","Control global exchange, margin, sourcing, and supply variables.")
        form=self.card(body);form.pack(anchor="nw",fill="x",ipadx=20,ipady=10)
        tk.Label(form,text="Business calculation defaults",bg=CARD,fg=INK,font=("Segoe UI Semibold",14)).grid(row=0,column=0,columnspan=2,sticky="w",padx=24,pady=(18,20))
        specs=[("RMB exchange rate (BDT)","rmb_rate"),("Retail margin (%)","retail_margin"),("Wholesale margin (%)","wholesale_margin"),("Total sourcing cost (RMB)","sourcing_cost_rmb"),("Company code prefix","company_prefix"),("Supply date (YYYY-MM-DD)","supply_date")]
        entries={}
        for i,(label,key) in enumerate(specs,1):
            tk.Label(form,text=label,bg=CARD,fg=INK,font=("Segoe UI Semibold",9)).grid(row=i,column=0,sticky="w",padx=24,pady=9)
            e=ttk.Entry(form,width=34);e.grid(row=i,column=1,sticky="ew",padx=24,pady=9);e.insert(0,self.db.setting(key));entries[key]=e
        form.columnconfigure(1,weight=1)
        def save():
            try:
                for key in ("rmb_rate","retail_margin","wholesale_margin","sourcing_cost_rmb"):float(entries[key].get())
                datetime.strptime(entries["supply_date"].get(),"%Y-%m-%d")
                if not entries["company_prefix"].get().strip():raise ValueError("Company prefix is required")
                self.db.set_settings({k:e.get().strip() for k,e in entries.items()});messagebox.showinfo("Settings saved","All calculations have been updated.")
            except ValueError as exc:messagebox.showerror("Invalid settings",str(exc))
        self.action_button(form,"Save and recalculate",save).grid(row=len(specs)+1,column=1,sticky="e",padx=24,pady=(18,22))


if __name__ == "__main__":
    App().mainloop()
