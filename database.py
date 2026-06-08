"""
Database Module V3 - Moka-style Full POS System
Features: Outlets, Product Variations, Tables, Kitchen Orders, Split Bill, Void, Audit Log, Notifications
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kasir_db.sqlite")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_database():
    conn = get_connection()
    c = conn.cursor()

    # ===== OUTLETS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS outlets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ===== USERS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'kasir',
            outlet_id INTEGER DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (outlet_id) REFERENCES outlets(id)
        )
    """)

    # ===== CATEGORIES =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#0984e3',
            icon TEXT DEFAULT '',
            outlet_id INTEGER DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ===== PRODUCTS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT,
            name TEXT NOT NULL,
            category_id INTEGER,
            buy_price REAL NOT NULL DEFAULT 0,
            sell_price REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 5,
            unit TEXT DEFAULT 'pcs',
            image_path TEXT DEFAULT '',
            has_variations INTEGER NOT NULL DEFAULT 0,
            is_food INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            outlet_id INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (outlet_id) REFERENCES outlets(id)
        )
    """)
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode) WHERE barcode IS NOT NULL AND barcode != ''")

    # ===== PRODUCT VARIATIONS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS product_variations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variation_name TEXT NOT NULL,
            variation_value TEXT NOT NULL,
            price_adjustment REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            sku TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    # ===== PRODUCT OUTLET PRICES =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS product_outlet_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            outlet_id INTEGER NOT NULL,
            sell_price REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (outlet_id) REFERENCES outlets(id),
            UNIQUE(product_id, outlet_id)
        )
    """)

    # ===== CUSTOMERS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            points INTEGER NOT NULL DEFAULT 0,
            total_spent REAL NOT NULL DEFAULT 0,
            total_visits INTEGER NOT NULL DEFAULT 0,
            tier TEXT NOT NULL DEFAULT 'Regular',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ===== PROMOS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'percentage',
            value REAL NOT NULL DEFAULT 0,
            min_purchase REAL NOT NULL DEFAULT 0,
            max_discount REAL DEFAULT 0,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            applicable_category_id INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ===== SHIFTS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            outlet_id INTEGER DEFAULT 1,
            start_time TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            end_time TEXT,
            start_cash REAL NOT NULL DEFAULT 0,
            end_cash REAL,
            total_transactions INTEGER NOT NULL DEFAULT 0,
            total_revenue REAL NOT NULL DEFAULT 0,
            total_cash REAL NOT NULL DEFAULT 0,
            total_non_cash REAL NOT NULL DEFAULT 0,
            difference REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'open',
            notes TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (outlet_id) REFERENCES outlets(id)
        )
    """)

    # ===== RESTAURANT TABLES =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS restaurant_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number INTEGER NOT NULL,
            name TEXT DEFAULT '',
            capacity INTEGER DEFAULT 4,
            status TEXT NOT NULL DEFAULT 'available',
            outlet_id INTEGER DEFAULT 1,
            floor INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(table_number, outlet_id)
        )
    """)

    # ===== TABLE ORDERS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS table_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            transaction_id INTEGER,
            order_number TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            customer_count INTEGER DEFAULT 1,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            closed_at TEXT,
            FOREIGN KEY (table_id) REFERENCES restaurant_tables(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    """)

    # ===== TRANSACTIONS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            shift_id INTEGER,
            outlet_id INTEGER DEFAULT 1,
            customer_id INTEGER,
            customer_name TEXT DEFAULT 'Umum',
            table_id INTEGER,
            table_order_id INTEGER,
            subtotal REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            discount_type TEXT DEFAULT 'manual',
            promo_id INTEGER,
            tax REAL NOT NULL DEFAULT 0,
            tax_rate REAL NOT NULL DEFAULT 0,
            service_charge REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            paid REAL NOT NULL DEFAULT 0,
            change_amount REAL NOT NULL DEFAULT 0,
            payment_method TEXT DEFAULT 'Tunai',
            points_used INTEGER NOT NULL DEFAULT 0,
            points_earned INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'completed',
            refund_reason TEXT DEFAULT '',
            is_voided INTEGER NOT NULL DEFAULT 0,
            void_reason TEXT DEFAULT '',
            voided_by INTEGER,
            voided_at TEXT,
            split_from INTEGER,
            is_offline INTEGER NOT NULL DEFAULT 0,
            custom_notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (shift_id) REFERENCES shifts(id),
            FOREIGN KEY (outlet_id) REFERENCES outlets(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (promo_id) REFERENCES promos(id),
            FOREIGN KEY (table_id) REFERENCES restaurant_tables(id),
            FOREIGN KEY (split_from) REFERENCES transactions(id)
        )
    """)

    # ===== TRANSACTION ITEMS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_price REAL NOT NULL,
            variation_id INTEGER,
            variation_text TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1,
            subtotal REAL NOT NULL,
            custom_note TEXT DEFAULT '',
            kitchen_status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (variation_id) REFERENCES product_variations(id)
        )
    """)

    # ===== STOCK HISTORY =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            note TEXT DEFAULT '',
            user_id INTEGER,
            outlet_id INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ===== POINT TRANSACTIONS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS point_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            transaction_id INTEGER,
            type TEXT NOT NULL,
            points INTEGER NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    """)

    # ===== NOTIFICATIONS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            related_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ===== AUDIT LOG =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            module TEXT NOT NULL,
            detail TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ===== OFFLINE QUEUE =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS offline_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            synced_at TEXT
        )
    """)

    # ===== PRINTER SETTINGS =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS printer_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            printer_type TEXT DEFAULT 'thermal',
            port TEXT DEFAULT '',
            paper_width INTEGER DEFAULT 58,
            auto_print INTEGER DEFAULT 1,
            outlet_id INTEGER DEFAULT 1
        )
    """)

    conn.commit()

    # ===== SEED DATA =====
    # Outlets
    c.execute("SELECT COUNT(*) FROM outlets")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO outlets (name, address, phone) VALUES ('Outlet Utama', 'Jl. Merdeka No. 123, Jakarta', '021-12345678')")
        c.execute("INSERT INTO outlets (name, address, phone) VALUES ('Cabang Sudirman', 'Jl. Sudirman No. 456, Jakarta', '021-87654321')")

    # Users
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, full_name, role, outlet_id) VALUES ('admin', 'admin123', 'Administrator', 'owner', 1)")
        c.execute("INSERT INTO users (username, password, full_name, role, outlet_id) VALUES ('kasir01', 'kasir123', 'Kasir Satu', 'kasir', 1)")
        c.execute("INSERT INTO users (username, password, full_name, role, outlet_id) VALUES ('manager01', 'manager123', 'Manager Utama', 'manager', 1)")
        c.execute("INSERT INTO users (username, password, full_name, role, outlet_id) VALUES ('kasir02', 'kasir123', 'Kasir Dua', 'kasir', 2)")

    # Categories
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        cats = [
            ('Makanan', 'Produk makanan berat', '#e17055', '🍽️', 1),
            ('Minuman', 'Produk minuman', '#0984e3', '🥤', 1),
            ('Snack', 'Camilan dan snack', '#fdcb6e', '🍿', 1),
            ('Sembako', 'Bahan pokok harian', '#00b894', '🛒', 1),
            ('Dessert', 'Makanan penutup', '#fd79a8', '🍰', 1),
            ('Kopi', 'Berbagai kopi', '#6c5ce7', '☕', 1),
        ]
        for name, desc, color, icon, oid in cats:
            c.execute("INSERT INTO categories (name, description, color, icon, outlet_id) VALUES (?,?,?,?,?)", (name, desc, color, icon, oid))

    # Products
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        prods = [
            ('8901234560001', 'Nasi Goreng', 1, 12000, 22000, 50, 10, 'porsi', 1, 1),
            ('8901234560002', 'Mie Goreng', 1, 10000, 18000, 50, 10, 'porsi', 1, 1),
            ('8901234560003', 'Ayam Goreng', 1, 15000, 28000, 30, 5, 'porsi', 1, 1),
            ('8901234560004', 'Sate Ayam', 1, 18000, 32000, 25, 5, 'porsi', 1, 1),
            ('8901234560005', 'Soto Ayam', 1, 10000, 20000, 40, 10, 'porsi', 1, 1),
            ('8901234560006', 'Bakso', 1, 12000, 22000, 45, 10, 'porsi', 1, 1),
            ('8901234560007', 'Gado-gado', 1, 10000, 18000, 35, 10, 'porsi', 1, 1),
            ('8901234560008', 'Es Teh Manis', 2, 2000, 6000, 100, 20, 'gelas', 0, 1),
            ('8901234560009', 'Es Jeruk', 2, 3000, 8000, 80, 15, 'gelas', 0, 1),
            ('8901234560010', 'Jus Alpukat', 2, 8000, 18000, 30, 10, 'gelas', 0, 1),
            ('8901234560011', 'Keripik Singkong', 3, 5000, 12000, 40, 10, 'bungkus', 0, 1),
            ('8901234560012', 'Kacang Goreng', 3, 6000, 14000, 35, 10, 'bungkus', 0, 1),
            ('8901234560013', 'Cireng', 3, 4000, 10000, 45, 10, 'bungkus', 0, 1),
            ('8901234560014', 'Beras 5kg', 4, 55000, 68000, 20, 5, 'karung', 0, 1),
            ('8901234560015', 'Minyak Goreng 1L', 4, 14000, 20000, 25, 5, 'botol', 0, 1),
            ('8901234560016', 'Gula Pasir 1kg', 4, 12000, 18000, 30, 5, 'bungkus', 0, 1),
            ('8901234560017', 'Kopi Susu', 6, 4000, 15000, 80, 15, 'gelas', 0, 1),
            ('8901234560018', 'Espresso', 6, 3000, 12000, 100, 20, 'gelas', 0, 1),
            ('8901234560019', 'Cappuccino', 6, 5000, 20000, 60, 10, 'gelas', 0, 1),
            ('8901234560020', 'Kopi Hitam', 6, 2000, 8000, 100, 20, 'gelas', 0, 1),
            ('8901234560021', 'Teh Tarik', 2, 3000, 12000, 70, 15, 'gelas', 0, 1),
            ('8901234560022', 'Pisang Goreng', 3, 3000, 8000, 50, 10, 'porsi', 0, 1),
            ('8901234560023', 'Rendang', 1, 25000, 40000, 20, 5, 'porsi', 1, 1),
            ('8901234560024', 'Es Krim', 5, 5000, 12000, 40, 10, 'cup', 0, 1),
        ]
        for p in prods:
            c.execute("INSERT INTO products (barcode, name, category_id, buy_price, sell_price, stock, min_stock, unit, is_food, outlet_id) VALUES (?,?,?,?,?,?,?,?,?,?)", p)

        # Product variations for Kopi Susu
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (17, 'Ukuran', 'Small', 0, 50)")
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (17, 'Ukuran', 'Medium', 5000, 40)")
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (17, 'Ukuran', 'Large', 10000, 30)")
        c.execute("UPDATE products SET has_variations=1 WHERE id=17")

        # Product variations for Cappuccino
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (19, 'Ukuran', 'Small', 0, 40)")
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (19, 'Ukuran', 'Medium', 5000, 35)")
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (19, 'Ukuran', 'Large', 10000, 25)")
        c.execute("UPDATE products SET has_variations=1 WHERE id=19")

        # Product variations for Nasi Goreng
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (1, 'Level', 'Biasa', 0, 30)")
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (1, 'Level', 'Pedas', 0, 20)")
        c.execute("INSERT INTO product_variations (product_id, variation_name, variation_value, price_adjustment, stock) VALUES (1, 'Level', 'Extra Pedas', 2000, 15)")
        c.execute("UPDATE products SET has_variations=1 WHERE id=1")

        # Outlet prices for cabang
        for pid in [1,2,3,8,17]:
            c.execute("SELECT sell_price FROM products WHERE id=?", (pid,))
            price = c.fetchone()[0]
            c.execute("INSERT OR IGNORE INTO product_outlet_prices (product_id, outlet_id, sell_price) VALUES (?, 2, ?)", (pid, int(price * 1.1)))

    # Customers
    c.execute("SELECT COUNT(*) FROM customers")
    if c.fetchone()[0] == 0:
        custs = [
            ('Budi Santoso', '08123456789', 'budi@email.com', 'Jl. Sudirman 10', 250, 1250000, 12, 'Gold'),
            ('Siti Rahayu', '08234567890', 'siti@email.com', 'Jl. Gatot Subroto 5', 180, 890000, 9, 'Silver'),
            ('Ahmad Fauzi', '08345678901', '', 'Jl. Thamrin 15', 50, 350000, 3, 'Regular'),
            ('Dewi Lestari', '08456789012', 'dewi@email.com', '', 320, 2100000, 15, 'Platinum'),
            ('Rudi Hermawan', '08567890123', '', '', 0, 0, 0, 'Regular'),
        ]
        for cust in custs:
            c.execute("INSERT INTO customers (name, phone, email, address, points, total_spent, total_visits, tier) VALUES (?,?,?,?,?,?,?,?)", cust)

    # Promos
    c.execute("SELECT COUNT(*) FROM promos")
    if c.fetchone()[0] == 0:
        now = datetime.now()
        promos = [
            ('Diskon Awal Bulan 10%', 'percentage', 10, 50000, 0, now.strftime('%Y-%m-01'), now.strftime('%Y-%m-10'), None),
            ('Hemat 25K', 'fixed', 25000, 100000, 0, now.strftime('%Y-%m-01'), now.strftime('%Y-%m-28'), None),
            ('Promo Makanan 15%', 'percentage', 15, 30000, 20000, now.strftime('%Y-%m-15'), now.strftime('%Y-%m-20'), 1),
            ('Happy Hour Coffee 20%', 'percentage', 20, 0, 15000, now.strftime('%Y-%m-01'), now.strftime('%Y-%m-30'), 6),
        ]
        for p in promos:
            c.execute("INSERT INTO promos (name, type, value, min_purchase, max_discount, start_date, end_date, applicable_category_id) VALUES (?,?,?,?,?,?,?,?)", p)

    # Restaurant Tables
    c.execute("SELECT COUNT(*) FROM restaurant_tables")
    if c.fetchone()[0] == 0:
        for i in range(1, 16):
            name_map = {1:'Melati', 2:'Mawar', 3:'Anggrek', 4:'Tulip', 5:'Dahlia',
                        6:'Lily', 7:'Sakura', 8:'Lavender', 9:'Violet', 10:'Iris',
                        11:'Peony', 12:'Matahari', 13:'Kamboja', 14:'Flamboyan', 15:'Kenanga'}
            cap = 8 if i <= 3 else (6 if i <= 8 else 4)
            c.execute("INSERT INTO restaurant_tables (table_number, name, capacity, status, floor) VALUES (?,?,?,?,?)",
                      (i, name_map.get(i, f'Meja {i}'), cap, 'available', 1 if i <= 10 else 2))

    # Printer settings
    c.execute("SELECT COUNT(*) FROM printer_settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO printer_settings (name, printer_type, paper_width, auto_print) VALUES ('Printer Utama', 'thermal', 58, 1)")
        c.execute("INSERT INTO printer_settings (name, printer_type, paper_width, auto_print) VALUES ('Kitchen Printer', 'thermal', 58, 1)")

    conn.commit()
    conn.close()


# ==================== USER OPERATIONS ====================
def verify_user(username, password):
    conn = get_connection()
    u = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND active=1", (username, password)).fetchone()
    conn.close()
    return dict(u) if u else None

def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT u.*, o.name as outlet_name FROM users u LEFT JOIN outlets o ON u.outlet_id=o.id ORDER BY u.created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_user(username, password, full_name, role, outlet_id=1):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO users (username,password,full_name,role,outlet_id) VALUES (?,?,?,?,?)", (username,password,full_name,role,outlet_id))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError: return False

def update_user(user_id, full_name, role, active, outlet_id=1):
    conn = get_connection()
    conn.execute("UPDATE users SET full_name=?,role=?,active=?,outlet_id=? WHERE id=?", (full_name,role,active,outlet_id,user_id))
    conn.commit(); conn.close(); return True

def update_user_password(user_id, new_password):
    conn = get_connection()
    conn.execute("UPDATE users SET password=? WHERE id=?", (new_password, user_id))
    conn.commit(); conn.close(); return True

def delete_user(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET active=0 WHERE id=?", (user_id,))
    conn.commit(); conn.close(); return True


# ==================== OUTLET OPERATIONS ====================
def get_all_outlets():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM outlets WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_outlet_by_id(oid):
    conn = get_connection()
    r = conn.execute("SELECT * FROM outlets WHERE id=?", (oid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def add_outlet(name, address='', phone=''):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO outlets (name,address,phone) VALUES (?,?,?)", (name,address,phone))
        conn.commit(); conn.close(); return True
    except: return False

def update_outlet(oid, name, address, phone):
    conn = get_connection()
    conn.execute("UPDATE outlets SET name=?,address=?,phone=? WHERE id=?", (name,address,phone,oid))
    conn.commit(); conn.close(); return True


# ==================== CATEGORY OPERATIONS ====================
def get_all_categories(outlet_id=None):
    conn = get_connection()
    if outlet_id:
        rows = conn.execute("SELECT * FROM categories WHERE active=1 AND (outlet_id=? OR outlet_id=1) ORDER BY name", (outlet_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM categories WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_category(name, description='', color='#0984e3', icon='', outlet_id=1):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO categories (name,description,color,icon,outlet_id) VALUES (?,?,?,?,?)", (name,description,color,icon,outlet_id))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError: return False

def update_category(cat_id, name, description, color='#0984e3', icon=''):
    conn = get_connection()
    conn.execute("UPDATE categories SET name=?,description=?,color=?,icon=? WHERE id=?", (name,description,color,icon,cat_id))
    conn.commit(); conn.close(); return True

def delete_category(cat_id):
    conn = get_connection()
    conn.execute("UPDATE categories SET active=0 WHERE id=?", (cat_id,))
    conn.commit(); conn.close(); return True


# ==================== PRODUCT OPERATIONS ====================
def get_all_products(active_only=True, outlet_id=None):
    conn = get_connection()
    q = """SELECT p.*, c.name as category_name, c.color as category_color, c.icon as category_icon
           FROM products p LEFT JOIN categories c ON p.category_id=c.id"""
    conds = []
    params = []
    if active_only: conds.append("p.active=1")
    if outlet_id: conds.append("(p.outlet_id=? OR p.outlet_id=1)"); params.append(outlet_id)
    if conds: q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY p.name"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_products_by_category(cat_id, outlet_id=None):
    conn = get_connection()
    q = """SELECT p.*, c.name as category_name, c.color as category_color
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.category_id=? AND p.active=1"""
    params = [cat_id]
    if outlet_id:
        q += " AND (p.outlet_id=? OR p.outlet_id=1)"
        params.append(outlet_id)
    q += " ORDER BY p.name"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_products(keyword, outlet_id=None):
    conn = get_connection()
    q = """SELECT p.*, c.name as category_name, c.color as category_color
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.active=1 AND (p.name LIKE ? OR p.barcode LIKE ?)"""
    params = [f'%{keyword}%', f'%{keyword}%']
    if outlet_id:
        q += " AND (p.outlet_id=? OR p.outlet_id=1)"
        params.append(outlet_id)
    q += " ORDER BY p.name LIMIT 50"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_product_by_id(pid):
    conn = get_connection()
    r = conn.execute("SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=?", (pid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def get_product_by_barcode(barcode):
    conn = get_connection()
    r = conn.execute("SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.barcode=? AND p.active=1", (barcode,)).fetchone()
    conn.close()
    return dict(r) if r else None

def add_product(barcode, name, cat_id, buy, sell, stock, min_stock, unit, is_food=0, has_variations=0, outlet_id=1):
    try:
        conn = get_connection()
        conn.execute("""INSERT INTO products (barcode,name,category_id,buy_price,sell_price,stock,min_stock,unit,is_food,has_variations,outlet_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (barcode,name,cat_id,buy,sell,stock,min_stock,unit,is_food,has_variations,outlet_id))
        conn.commit(); pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close(); return pid
    except sqlite3.IntegrityError: return None

def update_product(pid, barcode, name, cat_id, buy, sell, stock, min_stock, unit, active=1, is_food=0, has_variations=0):
    conn = get_connection()
    conn.execute("""UPDATE products SET barcode=?,name=?,category_id=?,buy_price=?,sell_price=?,
        stock=?,min_stock=?,unit=?,active=?,is_food=?,has_variations=?,updated_at=datetime('now','localtime') WHERE id=?""",
        (barcode,name,cat_id,buy,sell,stock,min_stock,unit,active,is_food,has_variations,pid))
    conn.commit(); conn.close(); return True

def delete_product(pid):
    conn = get_connection()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
    conn.commit(); conn.close(); return True


# ==================== PRODUCT VARIATION OPERATIONS ====================
def get_product_variations(product_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM product_variations WHERE product_id=? AND active=1", (product_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_product_variation(product_id, variation_name, variation_value, price_adjustment=0, stock=0, sku=''):
    conn = get_connection()
    conn.execute("INSERT INTO product_variations (product_id,variation_name,variation_value,price_adjustment,stock,sku) VALUES (?,?,?,?,?,?)",
        (product_id,variation_name,variation_value,price_adjustment,stock,sku))
    conn.commit(); conn.close(); return True

def update_product_variation(var_id, variation_name, variation_value, price_adjustment, stock, sku=''):
    conn = get_connection()
    conn.execute("UPDATE product_variations SET variation_name=?,variation_value=?,price_adjustment=?,stock=?,sku=? WHERE id=?",
        (variation_name,variation_value,price_adjustment,stock,sku,var_id))
    conn.commit(); conn.close(); return True

def delete_product_variation(var_id):
    conn = get_connection()
    conn.execute("UPDATE product_variations SET active=0 WHERE id=?", (var_id,))
    conn.commit(); conn.close(); return True


# ==================== PRODUCT OUTLET PRICES ====================
def get_product_outlet_price(product_id, outlet_id):
    conn = get_connection()
    r = conn.execute("SELECT * FROM product_outlet_prices WHERE product_id=? AND outlet_id=?", (product_id, outlet_id)).fetchone()
    conn.close()
    return dict(r) if r else None

def set_product_outlet_price(product_id, outlet_id, sell_price):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO product_outlet_prices (product_id,outlet_id,sell_price) VALUES (?,?,?)", (product_id,outlet_id,sell_price))
    conn.commit(); conn.close(); return True

def get_effective_price(product_id, outlet_id=1):
    op = get_product_outlet_price(product_id, outlet_id)
    if op: return op['sell_price']
    p = get_product_by_id(product_id)
    return p['sell_price'] if p else 0


# ==================== STOCK OPERATIONS ====================
def update_stock(pid, qty, typ, note='', user_id=None, outlet_id=1):
    conn = get_connection()
    conn.execute("UPDATE products SET stock=stock+? WHERE id=?", (qty,pid))
    conn.execute("INSERT INTO stock_history (product_id,type,quantity,note,user_id,outlet_id) VALUES (?,?,?,?,?,?)", (pid,typ,qty,note,user_id,outlet_id))
    # Check low stock notification
    p = conn.execute("SELECT name, stock, min_stock FROM products WHERE id=?", (pid,)).fetchone()
    if p and p['stock'] <= p['min_stock']:
        conn.execute("INSERT INTO notifications (type,title,message,related_id) VALUES (?,?,?,?)",
            ('low_stock', 'Stok Rendah', f"{p['name']} - Stok tersisa {p['stock']}", pid))
    conn.commit(); conn.close(); return True

def get_stock_history(product_id=None, limit=50):
    conn = get_connection()
    if product_id:
        rows = conn.execute("SELECT sh.*, p.name as product_name FROM stock_history sh LEFT JOIN products p ON sh.product_id=p.id WHERE sh.product_id=? ORDER BY sh.created_at DESC LIMIT ?", (product_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT sh.*, p.name as product_name FROM stock_history sh LEFT JOIN products p ON sh.product_id=p.id ORDER BY sh.created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_low_stock_products():
    conn = get_connection()
    rows = conn.execute("""SELECT p.*, c.name as category_name FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.active=1 AND p.stock<=p.min_stock ORDER BY p.stock ASC""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== CUSTOMER OPERATIONS ====================
def get_all_customers():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM customers WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_customers(keyword):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM customers WHERE active=1 AND (name LIKE ? OR phone LIKE ?)",
        (f'%{keyword}%', f'%{keyword}%')).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_customer_by_id(cid):
    conn = get_connection()
    r = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def add_customer(name, phone='', email='', address=''):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO customers (name,phone,email,address) VALUES (?,?,?,?)", (name,phone,email,address))
        conn.commit(); cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close(); return cid
    except: return None

def update_customer(cid, name, phone, email, address, tier):
    conn = get_connection()
    conn.execute("UPDATE customers SET name=?,phone=?,email=?,address=?,tier=?,updated_at=datetime('now','localtime') WHERE id=?",
        (name,phone,email,address,tier,cid))
    conn.commit(); conn.close(); return True


# ==================== PROMO OPERATIONS ====================
def get_all_promos():
    conn = get_connection()
    rows = conn.execute("SELECT p.*, c.name as category_name FROM promos p LEFT JOIN categories c ON p.applicable_category_id=c.id ORDER BY p.created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_promos():
    conn = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    rows = conn.execute("SELECT * FROM promos WHERE active=1 AND start_date<=? AND end_date>=?", (today,today)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_promo(name, typ, value, min_purchase, start_date, end_date, max_discount=0, category_id=None):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO promos (name,type,value,min_purchase,max_discount,start_date,end_date,applicable_category_id) VALUES (?,?,?,?,?,?,?,?)",
            (name,typ,value,min_purchase,max_discount,start_date,end_date,category_id))
        conn.commit(); conn.close(); return True
    except: return False

def update_promo(pid, name, typ, value, min_purchase, start_date, end_date, active, max_discount=0, category_id=None):
    conn = get_connection()
    conn.execute("UPDATE promos SET name=?,type=?,value=?,min_purchase=?,max_discount=?,start_date=?,end_date=?,active=?,applicable_category_id=? WHERE id=?",
        (name,typ,value,min_purchase,max_discount,start_date,end_date,active,category_id,pid))
    conn.commit(); conn.close(); return True

def delete_promo(pid):
    conn = get_connection()
    conn.execute("DELETE FROM promos WHERE id=?", (pid,))
    conn.commit(); conn.close(); return True

def calculate_promo_discount(promo, subtotal, category_items_total=None):
    if subtotal < promo['min_purchase']: return 0
    if promo.get('applicable_category_id') and category_items_total is not None:
        if category_items_total < promo['min_purchase']: return 0
        base = category_items_total
    else:
        base = subtotal
    if promo['type'] == 'percentage':
        disc = base * (promo['value'] / 100)
        if promo.get('max_discount') and promo['max_discount'] > 0:
            disc = min(disc, promo['max_discount'])
        return disc
    else:
        return min(promo['value'], subtotal)


# ==================== SHIFT OPERATIONS ====================
def open_shift(user_id, start_cash, outlet_id=1):
    conn = get_connection()
    conn.execute("INSERT INTO shifts (user_id,outlet_id,start_cash,status) VALUES (?,?,?,'open')", (user_id,outlet_id,start_cash))
    conn.commit(); sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close(); return sid

def close_shift(shift_id, end_cash, notes=''):
    conn = get_connection()
    shift = get_shift_by_id(shift_id)
    if not shift: conn.close(); return False

    rows = conn.execute("""SELECT COUNT(*) as tx_count, COALESCE(SUM(total),0) as revenue,
        COALESCE(SUM(CASE WHEN payment_method='Tunai' THEN total ELSE 0 END),0) as cash_total,
        COALESCE(SUM(CASE WHEN payment_method!='Tunai' THEN total ELSE 0 END),0) as non_cash
        FROM transactions WHERE shift_id=? AND is_voided=0""", (shift_id,)).fetchone()

    diff = end_cash - (shift['start_cash'] + rows['cash_total'])
    conn.execute("""UPDATE shifts SET end_time=datetime('now','localtime'), end_cash=?,
        total_transactions=?, total_revenue=?, total_cash=?, total_non_cash=?, difference=?, status='closed', notes=?
        WHERE id=?""", (end_cash, rows['tx_count'], rows['revenue'], rows['cash_total'], rows['non_cash'], diff, notes, shift_id))
    conn.commit(); conn.close(); return True

def get_active_shift(user_id=None):
    conn = get_connection()
    if user_id:
        r = conn.execute("SELECT * FROM shifts WHERE status='open' AND user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    else:
        r = conn.execute("SELECT * FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(r) if r else None

def get_shift_by_id(sid):
    conn = get_connection()
    r = conn.execute("SELECT s.*, u.full_name as cashier_name, o.name as outlet_name FROM shifts s LEFT JOIN users u ON s.user_id=u.id LEFT JOIN outlets o ON s.outlet_id=o.id WHERE s.id=?", (sid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def get_shift_history(limit=20):
    conn = get_connection()
    rows = conn.execute("""SELECT s.*, u.full_name as cashier_name, o.name as outlet_name FROM shifts s
        LEFT JOIN users u ON s.user_id=u.id LEFT JOIN outlets o ON s.outlet_id=o.id ORDER BY s.id DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== RESTAURANT TABLE OPERATIONS ====================
def get_all_tables(outlet_id=1):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM restaurant_tables WHERE outlet_id=? ORDER BY table_number", (outlet_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_table_by_id(tid):
    conn = get_connection()
    r = conn.execute("SELECT * FROM restaurant_tables WHERE id=?", (tid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def update_table_status(tid, status):
    conn = get_connection()
    conn.execute("UPDATE restaurant_tables SET status=? WHERE id=?", (status, tid))
    conn.commit(); conn.close(); return True

def add_table(table_number, name, capacity, outlet_id=1, floor=1):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO restaurant_tables (table_number,name,capacity,outlet_id,floor) VALUES (?,?,?,?,?)", (table_number,name,capacity,outlet_id,floor))
        conn.commit(); conn.close(); return True
    except: return False

def update_table(tid, table_number, name, capacity, floor):
    conn = get_connection()
    conn.execute("UPDATE restaurant_tables SET table_number=?,name=?,capacity=?,floor=? WHERE id=?", (table_number,name,capacity,floor,tid))
    conn.commit(); conn.close(); return True

def delete_table(tid):
    conn = get_connection()
    conn.execute("DELETE FROM restaurant_tables WHERE id=?", (tid,))
    conn.commit(); conn.close(); return True


# ==================== TABLE ORDER OPERATIONS ====================
def create_table_order(table_id, order_number, customer_count=1, notes=''):
    conn = get_connection()
    conn.execute("INSERT INTO table_orders (table_id,order_number,customer_count,notes,status) VALUES (?,?,?,?,'active')",
        (table_id, order_number, customer_count, notes))
    conn.execute("UPDATE restaurant_tables SET status='occupied' WHERE id=?", (table_id,))
    conn.commit(); oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close(); return oid

def get_active_table_order(table_id):
    conn = get_connection()
    r = conn.execute("SELECT * FROM table_orders WHERE table_id=? AND status='active' ORDER BY id DESC LIMIT 1", (table_id,)).fetchone()
    conn.close()
    return dict(r) if r else None

def close_table_order(table_order_id, transaction_id):
    conn = get_connection()
    to = conn.execute("SELECT * FROM table_orders WHERE id=?", (table_order_id,)).fetchone()
    if to:
        conn.execute("UPDATE table_orders SET status='closed', closed_at=datetime('now','localtime'), transaction_id=? WHERE id=?", (transaction_id, table_order_id))
        conn.execute("UPDATE restaurant_tables SET status='available' WHERE id=?", (to['table_id'],))
    conn.commit(); conn.close(); return True


# ==================== TRANSACTION OPERATIONS ====================
def generate_invoice_no():
    today = datetime.now().strftime('%Y%m%d')
    conn = get_connection()
    cnt = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(created_at)=date('now','localtime')").fetchone()[0] + 1
    conn.close()
    return f"INV-{today}-{cnt:04d}"

def create_transaction(user_id, customer_name, items, discount=0, tax_rate=0, service_charge=0,
                       paid=0, payment_method='Tunai', shift_id=None, customer_id=None,
                       promo_id=None, discount_type='manual', points_used=0, outlet_id=1,
                       table_id=None, table_order_id=None, custom_notes='', is_offline=0):
    conn = get_connection()
    try:
        today = datetime.now().strftime('%Y%m%d')
        cnt = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(created_at)=date('now','localtime')").fetchone()[0] + 1
        inv = f"INV-{today}-{cnt:04d}"

        subtotal = sum(i['subtotal'] for i in items)
        tax = subtotal * (tax_rate / 100)
        svc = service_charge
        total = subtotal - discount + tax + svc
        change = paid - total
        points_earned = int(total / 10000)

        conn.execute("""INSERT INTO transactions (invoice_no,user_id,shift_id,outlet_id,customer_id,customer_name,
            table_id,table_order_id,subtotal,discount,discount_type,promo_id,tax,tax_rate,service_charge,
            total,paid,change_amount,payment_method,points_used,points_earned,status,custom_notes,is_offline)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (inv,user_id,shift_id,outlet_id,customer_id,customer_name,table_id,table_order_id,
             subtotal,discount,discount_type,promo_id,tax,tax_rate,svc,total,paid,change,
             payment_method,points_used,points_earned,'completed',custom_notes,is_offline))

        tx_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for item in items:
            conn.execute("""INSERT INTO transaction_items (transaction_id,product_id,product_name,product_price,
                variation_id,variation_text,quantity,subtotal,custom_note,kitchen_status)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (tx_id, item['product_id'], item['product_name'], item['product_price'],
                 item.get('variation_id'), item.get('variation_text',''), item['quantity'], item['subtotal'],
                 item.get('custom_note',''), 'pending' if item.get('is_food') else 'done'))

            # Update stock
            conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (item['quantity'], item['product_id']))
            conn.execute("INSERT INTO stock_history (product_id,type,quantity,note,user_id,outlet_id) VALUES (?,'penjualan',?,?,?)",
                (item['product_id'], -item['quantity'], f"Inv: {inv}", user_id, outlet_id))

        # Update customer
        if customer_id:
            conn.execute("UPDATE customers SET total_spent=total_spent+?, total_visits=total_visits+1 WHERE id=?", (total, customer_id))
            if points_earned > 0:
                conn.execute("UPDATE customers SET points=points+? WHERE id=?", (points_earned, customer_id))
                conn.execute("INSERT INTO point_transactions (customer_id,transaction_id,type,points,description) VALUES (?,?,?,?,?)",
                    (customer_id, tx_id, 'earn', points_earned, f'Poin dari {inv}'))
            if points_used > 0:
                conn.execute("UPDATE customers SET points=points+? WHERE id=?", (-points_used, customer_id))
                conn.execute("INSERT INTO point_transactions (customer_id,transaction_id,type,points,description) VALUES (?,?,?,?,?)",
                    (customer_id, tx_id, 'redeem', -points_used, f'Redeem poin {inv}'))
            conn.execute("""UPDATE customers SET tier=CASE
                WHEN total_spent>=2000000 THEN 'Platinum'
                WHEN total_spent>=1000000 THEN 'Gold'
                WHEN total_spent>=500000 THEN 'Silver'
                ELSE 'Regular' END WHERE id=?""", (customer_id,))

        # Close table order if linked
        if table_order_id:
            conn.execute("UPDATE table_orders SET status='closed', closed_at=datetime('now','localtime'), transaction_id=? WHERE id=?", (tx_id, table_order_id))
            if table_id:
                conn.execute("UPDATE restaurant_tables SET status='available' WHERE id=?", (table_id,))

        # Audit log
        conn.execute("INSERT INTO audit_log (user_id,action,module,detail) VALUES (?,?,?,?)",
            (user_id, 'create', 'transaction', f'Invoice: {inv}, Total: {total}'))

        conn.commit(); conn.close(); return {'invoice_no': inv, 'tx_id': tx_id, 'total': total, 'change': change, 'points_earned': points_earned}
    except Exception as e:
        try: conn.rollback(); conn.close()
        except: pass
        print(f"TX Error: {e}"); return None

def refund_transaction(tx_id, reason='', user_id=None):
    conn = get_connection()
    try:
        tx = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        if not tx or tx['status'] == 'refunded': conn.close(); return False

        items = conn.execute("SELECT * FROM transaction_items WHERE transaction_id=?", (tx_id,)).fetchall()
        for item in items:
            conn.execute("UPDATE products SET stock=stock+? WHERE id=?", (item['quantity'], item['product_id']))
            conn.execute("INSERT INTO stock_history (product_id,type,quantity,note,user_id) VALUES (?,'refund',?,?,?)",
                (item['product_id'], item['quantity'], f"Refund Inv: {tx['invoice_no']}", user_id))

        conn.execute("UPDATE transactions SET status='refunded', refund_reason=? WHERE id=?", (reason, tx_id))

        if tx['customer_id']:
            if tx['points_earned'] > 0:
                conn.execute("UPDATE customers SET points=points-? WHERE id=?", (tx['points_earned'], tx['customer_id']))
                conn.execute("INSERT INTO point_transactions (customer_id,transaction_id,type,points,description) VALUES (?,?,?,?,?)",
                    (tx['customer_id'], tx_id, 'refund_earn', -tx['points_earned'], f'Refund poin {tx["invoice_no"]}'))
            if tx['points_used'] > 0:
                conn.execute("UPDATE customers SET points=points+? WHERE id=?", (tx['points_used'], tx['customer_id']))
                conn.execute("INSERT INTO point_transactions (customer_id,transaction_id,type,points,description) VALUES (?,?,?,?,?)",
                    (tx['customer_id'], tx_id, 'refund_redeem', tx['points_used'], f'Refund redeem {tx["invoice_no"]}'))

        if user_id:
            conn.execute("INSERT INTO audit_log (user_id,action,module,detail) VALUES (?,?,?,?)",
                (user_id, 'refund', 'transaction', f'Invoice: {tx["invoice_no"]}, Reason: {reason}'))

        conn.commit(); conn.close(); return True
    except Exception as e:
        try: conn.rollback(); conn.close()
        except: pass
        print(f"Refund Error: {e}"); return False

def void_transaction(tx_id, reason='', user_id=None):
    conn = get_connection()
    try:
        tx = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        if not tx or tx['is_voided']: conn.close(); return False

        # Restore stock
        items = conn.execute("SELECT * FROM transaction_items WHERE transaction_id=?", (tx_id,)).fetchall()
        for item in items:
            conn.execute("UPDATE products SET stock=stock+? WHERE id=?", (item['quantity'], item['product_id']))

        conn.execute("UPDATE transactions SET is_voided=1, void_reason=?, voided_by=?, voided_at=datetime('now','localtime') WHERE id=?",
            (reason, user_id, tx_id))

        if user_id:
            conn.execute("INSERT INTO audit_log (user_id,action,module,detail) VALUES (?,?,?,?)",
                (user_id, 'void', 'transaction', f'Invoice: {tx["invoice_no"]}, Reason: {reason}'))

        conn.commit(); conn.close(); return True
    except Exception as e:
        try: conn.rollback(); conn.close()
        except: pass
        print(f"Void Error: {e}"); return False

def get_transactions_by_date(start, end, outlet_id=None):
    conn = get_connection()
    q = """SELECT t.*, u.full_name as cashier_name, o.name as outlet_name
        FROM transactions t LEFT JOIN users u ON t.user_id=u.id LEFT JOIN outlets o ON t.outlet_id=o.id
        WHERE date(t.created_at) BETWEEN ? AND ?"""
    params = [start, end]
    if outlet_id: q += " AND t.outlet_id=?"; params.append(outlet_id)
    q += " ORDER BY t.created_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_transaction_detail(tx_id):
    conn = get_connection()
    r = conn.execute("""SELECT t.*, u.full_name as cashier_name, o.name as outlet_name
        FROM transactions t LEFT JOIN users u ON t.user_id=u.id LEFT JOIN outlets o ON t.outlet_id=o.id WHERE t.id=?""", (tx_id,)).fetchone()
    if not r: conn.close(); return None
    result = dict(r)
    result['items'] = [dict(row) for row in conn.execute("SELECT * FROM transaction_items WHERE transaction_id=?", (tx_id,)).fetchall()]
    conn.close(); return result

def get_transaction_by_invoice(inv):
    conn = get_connection()
    r = conn.execute("SELECT id FROM transactions WHERE invoice_no=?", (inv,)).fetchone()
    conn.close()
    return get_transaction_detail(r['id']) if r else None


# ==================== NOTIFICATION OPERATIONS ====================
def get_unread_notifications():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM notifications WHERE is_read=0 ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_notifications(limit=30):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_notification_read(nid):
    conn = get_connection()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=?", (nid,))
    conn.commit(); conn.close()

def clear_notifications():
    conn = get_connection()
    conn.execute("DELETE FROM notifications")
    conn.commit(); conn.close()


# ==================== REPORT OPERATIONS ====================
def get_daily_summary(date=None, outlet_id=None):
    if not date: date = datetime.now().strftime('%Y-%m-%d')
    conn = get_connection()
    q = """SELECT COUNT(*) as total_transactions,
        COALESCE(SUM(CASE WHEN status!='refunded' AND is_voided=0 THEN total ELSE 0 END),0) as total_revenue,
        COALESCE(SUM(CASE WHEN status!='refunded' AND is_voided=0 THEN subtotal ELSE 0 END),0) as total_subtotal,
        COALESCE(SUM(discount),0) as total_discount,
        COALESCE(SUM(tax),0) as total_tax,
        COALESCE(SUM(service_charge),0) as total_service,
        COALESCE(SUM(CASE WHEN payment_method='Tunai' AND status!='refunded' AND is_voided=0 THEN total ELSE 0 END),0) as cash_total,
        COALESCE(SUM(CASE WHEN payment_method!='Tunai' AND status!='refunded' AND is_voided=0 THEN total ELSE 0 END),0) as non_cash_total,
        COUNT(CASE WHEN status='refunded' THEN 1 END) as refund_count,
        COUNT(CASE WHEN is_voided=1 THEN 1 END) as void_count
        FROM transactions WHERE date(created_at)=?"""
    params = [date]
    if outlet_id: q += " AND outlet_id=?"; params.append(outlet_id)
    row = conn.execute(q, params).fetchone()
    summary = dict(row)

    q2 = """SELECT ti.product_name, SUM(ti.quantity) as total_qty, SUM(ti.subtotal) as total_sales
        FROM transaction_items ti JOIN transactions t ON ti.transaction_id=t.id
        WHERE date(t.created_at)=? AND t.status!='refunded' AND t.is_voided=0"""
    params2 = [date]
    if outlet_id: q2 += " AND t.outlet_id=?"; params2.append(outlet_id)
    q2 += " GROUP BY ti.product_id ORDER BY total_qty DESC LIMIT 10"
    rows = conn.execute(q2, params2).fetchall()
    summary['top_products'] = [dict(r) for r in rows]
    conn.close()
    return summary

def get_monthly_summary(year, month, outlet_id=None):
    conn = get_connection()
    q = """SELECT COUNT(*) as total_transactions,
        COALESCE(SUM(CASE WHEN status!='refunded' AND is_voided=0 THEN total ELSE 0 END),0) as total_revenue,
        COALESCE(SUM(CASE WHEN status!='refunded' AND is_voided=0 THEN subtotal ELSE 0 END),0) as total_subtotal,
        COALESCE(SUM(discount),0) as total_discount,
        COALESCE(SUM(tax),0) as total_tax,
        COALESCE(SUM(service_charge),0) as total_service
        FROM transactions WHERE strftime('%Y',created_at)=? AND strftime('%m',created_at)=?"""
    params = [str(year), f'{month:02d}']
    if outlet_id: q += " AND outlet_id=?"; params.append(outlet_id)
    row = conn.execute(q, params).fetchone()
    summary = dict(row)

    q2 = """SELECT date(created_at) as date, COUNT(*) as transactions, SUM(total) as revenue
        FROM transactions WHERE strftime('%Y',created_at)=? AND strftime('%m',created_at)=? AND status!='refunded' AND is_voided=0"""
    params2 = [str(year), f'{month:02d}']
    if outlet_id: q2 += " AND outlet_id=?"; params2.append(outlet_id)
    q2 += " GROUP BY date(created_at) ORDER BY date"
    rows = conn.execute(q2, params2).fetchall()
    summary['daily_breakdown'] = [dict(r) for r in rows]
    conn.close()
    return summary

def get_sales_chart_data(days=30, outlet_id=None):
    conn = get_connection()
    q = """SELECT date(created_at) as date, COUNT(*) as transactions,
        COALESCE(SUM(CASE WHEN status!='refunded' AND is_voided=0 THEN total ELSE 0 END),0) as revenue
        FROM transactions WHERE date(created_at)>=date('now','-'||?||' days','localtime')"""
    params = [days]
    if outlet_id: q += " AND outlet_id=?"; params.append(outlet_id)
    q += " GROUP BY date(created_at) ORDER BY date"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_profit_data(days=30):
    conn = get_connection()
    rows = conn.execute("""SELECT date(t.created_at) as date,
        COALESCE(SUM(ti.subtotal),0) as revenue,
        COALESCE(SUM((ti.product_price - p.buy_price)*ti.quantity),0) as profit
        FROM transactions t JOIN transaction_items ti ON t.id=ti.transaction_id
        JOIN products p ON ti.product_id=p.id
        WHERE date(t.created_at)>=date('now','-'||?||' days','localtime') AND t.status!='refunded' AND t.is_voided=0
        GROUP BY date(t.created_at) ORDER BY date""", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_category_sales_data():
    conn = get_connection()
    rows = conn.execute("""SELECT c.name as category, c.color, SUM(ti.subtotal) as total_sales, SUM(ti.quantity) as total_qty
        FROM transaction_items ti JOIN products p ON ti.product_id=p.id
        JOIN categories c ON p.category_id=c.id
        JOIN transactions t ON ti.transaction_id=t.id WHERE t.status!='refunded' AND t.is_voided=0
        GROUP BY c.id ORDER BY total_sales DESC""").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_payment_method_data(days=30):
    conn = get_connection()
    rows = conn.execute("""SELECT payment_method, COUNT(*) as count, SUM(total) as total
        FROM transactions WHERE status!='refunded' AND is_voided=0
        AND date(created_at)>=date('now','-'||?||' days','localtime')
        GROUP BY payment_method""", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_peak_hours_data(days=30):
    conn = get_connection()
    rows = conn.execute("""SELECT strftime('%H', created_at) as hour, COUNT(*) as transactions, SUM(total) as revenue
        FROM transactions WHERE status!='refunded' AND is_voided=0
        AND date(created_at)>=date('now','-'||?||' days','localtime')
        GROUP BY strftime('%H', created_at) ORDER BY hour""", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_employee_performance(days=30):
    conn = get_connection()
    rows = conn.execute("""SELECT u.full_name, u.role, COUNT(t.id) as total_transactions,
        COALESCE(SUM(t.total),0) as total_revenue, COALESCE(AVG(t.total),0) as avg_transaction
        FROM transactions t JOIN users u ON t.user_id=u.id
        WHERE t.status!='refunded' AND t.is_voided=0
        AND date(t.created_at)>=date('now','-'||?||' days','localtime')
        GROUP BY t.user_id ORDER BY total_revenue DESC""", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_hourly_sales_today():
    conn = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    rows = conn.execute("""SELECT strftime('%H', created_at) as hour,
        COUNT(*) as transactions, COALESCE(SUM(total),0) as revenue
        FROM transactions WHERE date(created_at)=? AND status!='refunded' AND is_voided=0
        GROUP BY strftime('%H', created_at) ORDER BY hour""", (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_realtime_revenue():
    conn = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    r = conn.execute("""SELECT COALESCE(SUM(total),0) as revenue, COUNT(*) as count
        FROM transactions WHERE date(created_at)=? AND status!='refunded' AND is_voided=0""", (today,)).fetchone()
    conn.close()
    return dict(r) if r else {'revenue': 0, 'count': 0}


# ==================== AUDIT LOG ====================
def add_audit_log(user_id, action, module, detail=''):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO audit_log (user_id,action,module,detail) VALUES (?,?,?,?)", (user_id,action,module,detail))
        conn.commit(); conn.close()
    except: pass

def get_audit_logs(limit=50):
    conn = get_connection()
    rows = conn.execute("""SELECT a.*, u.full_name as user_name FROM audit_log a
        LEFT JOIN users u ON a.user_id=u.id ORDER BY a.created_at DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== OFFLINE QUEUE ====================
def queue_offline_action(action, data):
    conn = get_connection()
    conn.execute("INSERT INTO offline_queue (action,data) VALUES (?,?)", (action, json.dumps(data)))
    conn.commit(); conn.close()

def get_pending_offline():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM offline_queue WHERE status='pending' ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_offline_synced(qid):
    conn = get_connection()
    conn.execute("UPDATE offline_queue SET status='synced', synced_at=datetime('now','localtime') WHERE id=?", (qid,))
    conn.commit(); conn.close()


# ==================== PRINTER SETTINGS ====================
def get_printer_settings(outlet_id=1):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM printer_settings WHERE outlet_id=?", (outlet_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_printer_setting(pid, **kwargs):
    conn = get_connection()
    sets = ", ".join(f"{k}=?" for k in kwargs.keys())
    vals = list(kwargs.values()) + [pid]
    conn.execute(f"UPDATE printer_settings SET {sets} WHERE id=?", vals)
    conn.commit(); conn.close()


if __name__ == "__main__":
    init_database()
    print("Database V3 initialized successfully!")
    print("Tables: outlets, users, categories, products, product_variations, product_outlet_prices,")
    print("  customers, promos, shifts, restaurant_tables, table_orders, transactions,")
    print("  transaction_items, stock_history, point_transactions, notifications,")
    print("  audit_log, offline_queue, printer_settings")
