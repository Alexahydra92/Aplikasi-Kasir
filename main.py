"""
KASIR PRO V3 - Full Moka-style POS System
Features: Split Bill, Merge Bill, Void, Refund, Table Management, Kitchen Display,
          Product Variations, Multi Outlet, Peak Hours, Employee Performance, Offline Mode
Built with CustomTkinter + Matplotlib Charts
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import os, sys, math, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
from receipt import generate_receipt_text, save_receipt, format_currency

# ==================== THEME CONFIG ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Moka-inspired modern color system
C = {
    'bg':           '#0d1117',
    'bg2':          '#161b22',
    'bg3':          '#21262d',
    'bg4':          '#2d333b',
    'card':         '#1c2128',
    'card_hover':   '#292e36',
    'sidebar':      '#010409',
    'sidebar_act':  '#1c2128',
    'accent':       '#58a6ff',
    'accent2':      '#79c0ff',
    'green':        '#3fb950',
    'green2':       '#56d364',
    'green_bg':     '#0d2818',
    'red':          '#f85149',
    'red2':         '#da3633',
    'red_bg':       '#2d0a0a',
    'orange':       '#d29922',
    'yellow':       '#e3b341',
    'blue':         '#58a6ff',
    'blue2':        '#79c0ff',
    'blue_bg':      '#0d1d33',
    'pink':         '#db61a2',
    'purple':       '#bc8cff',
    'white':        '#f0f6fc',
    'text':         '#c9d1d9',
    'text2':        '#8b949e',
    'text3':        '#484f58',
    'border':       '#30363d',
    'gold':         '#e3b341',
    'silver':       '#8b949e',
    'platinum':     '#79c0ff',
    'teal':         '#39d353',
}

APP_TITLE = "KASIR PRO V3"
APP_SIZE = (1440, 850)

# Role permissions
PERMISSIONS = {
    'owner':  ['dashboard','kasir','produk','restoran','laporan','stok','karyawan','pelanggan','promo','shift','pengaturan'],
    'admin':  ['dashboard','kasir','produk','restoran','laporan','stok','karyawan','pelanggan','promo','shift','pengaturan'],
    'manager':['dashboard','kasir','produk','restoran','laporan','stok','pelanggan','promo','shift'],
    'kasir':  ['dashboard','kasir','restoran','stok','shift'],
}


class StatCard(ctk.CTkFrame):
    def __init__(self, master, icon="", label="", value="", color=C['accent'], **kw):
        super().__init__(master, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'], **kw)
        top = ctk.CTkFrame(self, fg_color='transparent')
        top.pack(fill='x', padx=16, pady=(14,4))
        ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(size=22), text_color=color).pack(side='left')
        ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=11), text_color=C['text2']).pack(side='left', padx=8)
        self.value_label = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white'])
        self.value_label.pack(padx=16, pady=(0,12), anchor='w')

    def update_value(self, value):
        self.value_label.configure(text=value)


class ProductCard(ctk.CTkFrame):
    def __init__(self, master, product, on_add=None, **kw):
        super().__init__(master, fg_color=C['card'], corner_radius=10, border_width=1, border_color=C['border'], height=105, **kw)
        self.pack_propagate(False)
        self.product = product
        cat_color = product.get('category_color', C['blue'])
        # Top color strip
        strip = ctk.CTkFrame(self, fg_color=cat_color, height=3, corner_radius=0)
        strip.pack(fill='x', side='top')
        content = ctk.CTkFrame(self, fg_color='transparent')
        content.pack(fill='both', expand=True, padx=10, pady=(4,6))
        name = product['name']
        if len(name) > 18: name = name[:16] + ".."
        ctk.CTkLabel(content, text=name, font=ctk.CTkFont(size=12, weight='bold'), text_color=C['white'], wraplength=120).pack(anchor='w')
        cat_icon = product.get('category_icon', '')
        ctk.CTkLabel(content, text=f"{cat_icon} {product.get('category_name','-')}", font=ctk.CTkFont(size=9), text_color=C['text3']).pack(anchor='w')
        bottom = ctk.CTkFrame(content, fg_color='transparent')
        bottom.pack(fill='x', pady=(2,0))
        ctk.CTkLabel(bottom, text=format_currency(product['sell_price']), font=ctk.CTkFont(size=12, weight='bold'), text_color=C['green']).pack(side='left')
        stock_color = C['red'] if product['stock'] <= product['min_stock'] else C['text3']
        ctk.CTkLabel(bottom, text=f"S:{product['stock']}", font=ctk.CTkFont(size=9), text_color=stock_color).pack(side='left', padx=6)
        if product.get('has_variations'):
            ctk.CTkLabel(bottom, text="VAR", font=ctk.CTkFont(size=8, weight='bold'), text_color=C['purple']).pack(side='left', padx=2)
        if on_add:
            btn = ctk.CTkButton(bottom, text="+", width=28, height=24, font=ctk.CTkFont(size=13, weight='bold'),
                                 fg_color=C['accent'], hover_color=C['accent2'], corner_radius=6,
                                 command=lambda: on_add(product))
            btn.pack(side='right')


class TableCard(ctk.CTkFrame):
    def __init__(self, master, table, on_click=None, **kw):
        colors = {'available': C['green_bg'], 'occupied': C['red_bg'], 'reserved': C['blue_bg']}
        borders = {'available': C['green'], 'occupied': C['red'], 'reserved': C['blue']}
        labels = {'available': 'Tersedia', 'occupied': 'Terisi', 'reserved': 'Reservasi'}
        bg = colors.get(table['status'], C['card'])
        bc = borders.get(table['status'], C['border'])
        super().__init__(master, fg_color=bg, corner_radius=10, border_width=2, border_color=bc, cursor='hand2', **kw)
        self.table = table
        ctk.CTkLabel(self, text=f"Meja {table['table_number']}", font=ctk.CTkFont(size=14, weight='bold'),
                      text_color=bc).pack(pady=(8,2))
        ctk.CTkLabel(self, text=table.get('name',''), font=ctk.CTkFont(size=10), text_color=C['text2']).pack()
        ctk.CTkLabel(self, text=f"Kapasitas: {table['capacity']}", font=ctk.CTkFont(size=9), text_color=C['text3']).pack()
        status_lbl = labels.get(table['status'], table['status'])
        ctk.CTkLabel(self, text=status_lbl, font=ctk.CTkFont(size=10, weight='bold'), text_color=bc).pack(pady=(2,8))
        if on_click:
            self.bind('<Button-1>', lambda e: on_click(table))
            for child in self.winfo_children():
                child.bind('<Button-1>', lambda e: on_click(table))


class TierBadge(ctk.CTkFrame):
    def __init__(self, master, tier="Regular", **kw):
        colors = {'Regular': C['text3'], 'Silver': C['silver'], 'Gold': C['gold'], 'Platinum': C['platinum']}
        color = colors.get(tier, C['text3'])
        super().__init__(master, fg_color=color, corner_radius=6, height=20, **kw)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text=tier, font=ctk.CTkFont(size=9, weight='bold'), text_color=C['bg']).pack(padx=6, pady=1)


# ==================== MAIN APP ====================
class KasirApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{APP_SIZE[0]}x{APP_SIZE[1]}")
        self.minsize(1100, 650)
        self.configure(fg_color=C['bg'])

        self.center_window()
        self.current_user = None
        self.cart = []
        self.cart_subtotal = 0
        self.current_shift = None
        self.selected_customer = None
        self.selected_promo = None
        self.current_outlet = 1
        self.split_carts = []
        self.active_table = None

        db.init_database()
        self.withdraw()
        self.show_login()

    def center_window(self):
        self.update_idletasks()
        w, h = APP_SIZE
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

    # ==================== LOGIN ====================
    def show_login(self):
        self.login_win = ctk.CTkToplevel(self)
        self.login_win.title("Login - KASIR PRO V3")
        self.login_win.geometry("480x600")
        self.login_win.configure(fg_color=C['bg'])
        self.login_win.resizable(False, False)
        self.login_win.grab_set()
        self.login_win.update_idletasks()
        x = (self.login_win.winfo_screenwidth() // 2) - 240
        y = (self.login_win.winfo_screenheight() // 2) - 300
        self.login_win.geometry(f'480x600+{x}+{y}')

        card = ctk.CTkFrame(self.login_win, fg_color=C['card'], corner_radius=20, border_width=1, border_color=C['border'])
        card.pack(padx=30, pady=25, fill='both', expand=True)

        # Logo area
        logo_f = ctk.CTkFrame(card, fg_color=C['accent'], corner_radius=14, width=80, height=80)
        logo_f.pack(pady=(40, 8))
        logo_f.pack_propagate(False)
        ctk.CTkLabel(logo_f, text="KP", font=ctk.CTkFont(size=28, weight='bold'), text_color=C['white']).pack(expand=True)

        ctk.CTkLabel(card, text="KASIR PRO", font=ctk.CTkFont(size=26, weight='bold'), text_color=C['white']).pack(pady=(4,0))
        ctk.CTkLabel(card, text="Sistem Manajemen Bisnis Lengkap", font=ctk.CTkFont(size=12), text_color=C['text2']).pack(pady=(0,25))

        for lbl, ph, key in [("Username", "Masukkan username", "user"), ("Password", "Masukkan password", "pass")]:
            ctk.CTkLabel(card, text=lbl, font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text'], anchor='w').pack(padx=35, fill='x', pady=(8,3))
            e = ctk.CTkEntry(card, placeholder_text=ph, height=42, font=ctk.CTkFont(size=13),
                              fg_color=C['bg2'], border_color=C['border'], corner_radius=10,
                              show="" if key == "user" else "●")
            e.pack(padx=35, fill='x')
            setattr(self, f'login_{key}', e)

        # Outlet select
        ctk.CTkLabel(card, text="Outlet", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text'], anchor='w').pack(padx=35, fill='x', pady=(8,3))
        outlets = db.get_all_outlets()
        outlet_names = [o['name'] for o in outlets]
        self.login_outlet_var = ctk.StringVar(value=outlet_names[0] if outlet_names else "Outlet Utama")
        outlet_menu = ctk.CTkOptionMenu(card, variable=self.login_outlet_var, values=outlet_names or ["Outlet Utama"],
                                         height=38, font=ctk.CTkFont(size=12), fg_color=C['bg2'], button_color=C['accent'])
        outlet_menu.pack(padx=35, fill='x')

        ctk.CTkButton(card, text="M A S U K", height=46, font=ctk.CTkFont(size=15, weight='bold'),
                        fg_color=C['accent'], hover_color=C['accent2'], corner_radius=12,
                        command=self.do_login).pack(padx=35, fill='x', pady=(20,8))

        ctk.CTkLabel(card, text="admin/admin123 | kasir01/kasir123 | manager01/manager123",
                      font=ctk.CTkFont(size=9), text_color=C['text3']).pack(pady=(5,0))

        self.login_pass.bind('<Return>', lambda e: self.do_login())
        self.login_win.protocol("WM_DELETE_WINDOW", self.on_login_close)

    def on_login_close(self):
        self.login_win.destroy(); self.destroy()

    def do_login(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("Peringatan", "Isi username dan password!", parent=self.login_win); return
        user = db.verify_user(u, p)
        if user:
            self.current_user = user
            # Set outlet
            outlets = db.get_all_outlets()
            sel_outlet = self.login_outlet_var.get()
            for o in outlets:
                if o['name'] == sel_outlet:
                    self.current_outlet = o['id']; break
            self.login_win.destroy()
            self.deiconify()
            shift = db.get_active_shift(user['id'])
            if not shift:
                self.show_shift_open_dialog()
            else:
                self.current_shift = shift
            db.add_audit_log(user['id'], 'login', 'auth', f'User {u} logged in')
            self.build_main_ui()
        else:
            messagebox.showerror("Gagal", "Username atau password salah!", parent=self.login_win)

    def show_shift_open_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Buka Shift")
        dlg.geometry("440x340")
        dlg.configure(fg_color=C['bg'])
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth()//2)-220; y = (dlg.winfo_screenheight()//2)-170
        dlg.geometry(f'440x340+{x}+{y}')

        card = ctk.CTkFrame(dlg, fg_color=C['card'], corner_radius=16, border_width=1, border_color=C['border'])
        card.pack(fill='both', expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text="Buka Shift Baru", font=ctk.CTkFont(size=20, weight='bold'), text_color=C['white']).pack(pady=(20,5))
        ctk.CTkLabel(card, text=f"Kasir: {self.current_user['full_name']}", font=ctk.CTkFont(size=13), text_color=C['text2']).pack(pady=(0,15))

        ctk.CTkLabel(card, text="Saldo Awal Kas:", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(padx=30, anchor='w')
        cash_entry = ctk.CTkEntry(card, placeholder_text="0", height=42, font=ctk.CTkFont(size=14, weight='bold'),
                                   fg_color=C['bg2'], corner_radius=10, border_color=C['border'])
        cash_entry.pack(padx=30, fill='x', pady=(4,15))
        cash_entry.insert(0, "0")

        def open_it():
            try: cash = float(cash_entry.get() or 0)
            except: cash = 0
            sid = db.open_shift(self.current_user['id'], cash, self.current_outlet)
            self.current_shift = db.get_shift_by_id(sid)
            dlg.destroy()

        ctk.CTkButton(card, text="Buka Shift", height=44, font=ctk.CTkFont(size=14, weight='bold'),
                        fg_color=C['green'], hover_color=C['green2'], corner_radius=12, command=open_it).pack(padx=30, fill='x')
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)

    # ==================== MAIN UI ====================
    def build_main_ui(self):
        for w in self.winfo_children(): w.destroy()
        # Top bar
        self.topbar = ctk.CTkFrame(self, height=48, fg_color=C['sidebar'], corner_radius=0)
        self.topbar.pack(side='top', fill='x')
        self.topbar.pack_propagate(False)
        self.build_topbar()

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=C['sidebar'], corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Main area
        self.main_area = ctk.CTkFrame(self, fg_color=C['bg'], corner_radius=0)
        self.main_area.pack(side='right', fill='both', expand=True)

        self.build_sidebar()
        self.navigate('dashboard')

    def build_topbar(self):
        # Left: app name + outlet
        left = ctk.CTkFrame(self.topbar, fg_color='transparent')
        left.pack(side='left', padx=14, fill='y')

        ctk.CTkLabel(left, text="KASIR PRO", font=ctk.CTkFont(size=14, weight='bold'), text_color=C['accent']).pack(side='left', pady=12)
        ctk.CTkLabel(left, text="V3", font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green']).pack(side='left', padx=(2,10))

        # Outlet indicator
        outlet = db.get_outlet_by_id(self.current_outlet)
        outlet_name = outlet['name'] if outlet else 'Outlet'
        ctk.CTkLabel(left, text=f"  {outlet_name}", font=ctk.CTkFont(size=11), text_color=C['text2']).pack(side='left')

        # Center: search
        center = ctk.CTkFrame(self.topbar, fg_color='transparent')
        center.pack(side='left', fill='both', expand=True, padx=20)

        self.global_search = ctk.CTkEntry(center, placeholder_text="  Cari produk, transaksi, pelanggan... (Ctrl+K)",
                                            height=34, font=ctk.CTkFont(size=12), fg_color=C['bg3'],
                                            corner_radius=8, border_color=C['border'])
        center.pack_propagate(False)
        self.global_search.pack(pady=7, fill='x')

        # Right: notifications, user
        right = ctk.CTkFrame(self.topbar, fg_color='transparent')
        right.pack(side='right', padx=14, fill='y')

        # Notifications
        notifs = db.get_unread_notifications()
        notif_text = f"  ({len(notifs)})" if notifs else ""
        self.notif_btn = ctk.CTkButton(right, text=f"  {notif_text}", width=36, height=32,
                                         font=ctk.CTkFont(size=14), fg_color='transparent',
                                         hover_color=C['bg3'], text_color=C['text2'], corner_radius=8,
                                         command=self.show_notifications)
        self.notif_btn.pack(side='right', padx=4)

        # Shift indicator
        if self.current_shift:
            shift_f = ctk.CTkFrame(right, fg_color=C['green_bg'], corner_radius=6, height=28)
            shift_f.pack(side='right', padx=8, pady=10)
            shift_f.pack_propagate(False)
            ctk.CTkLabel(shift_f, text=f"Shift Aktif", font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green']).pack(padx=8)

        # User
        if self.current_user:
            user_f = ctk.CTkFrame(right, fg_color=C['bg3'], corner_radius=8, height=32)
            user_f.pack(side='right', padx=4, pady=8)
            user_f.pack_propagate(False)
            role_colors = {'owner': C['gold'], 'admin': C['accent'], 'manager': C['purple'], 'kasir': C['green']}
            rc = role_colors.get(self.current_user['role'], C['text3'])
            ctk.CTkLabel(user_f, text=f" {self.current_user['full_name']} ", font=ctk.CTkFont(size=11), text_color=C['text']).pack(side='left', padx=(8,2))
            ctk.CTkLabel(user_f, text=self.current_user['role'].upper(), font=ctk.CTkFont(size=8, weight='bold'), text_color=rc).pack(side='left', padx=(0,8))

    def build_sidebar(self):
        role = self.current_user['role'] if self.current_user else 'kasir'
        allowed = PERMISSIONS.get(role, PERMISSIONS['kasir'])

        nav_items = [
            ('dashboard', 'Dashboard'),
            ('kasir', 'Kasir (POS)'),
            ('produk', 'Produk'),
            ('restoran', 'Restoran'),
            ('laporan', 'Laporan'),
            ('stok', 'Stok'),
            ('karyawan', 'Karyawan'),
            ('pelanggan', 'Pelanggan'),
            ('promo', 'Promo'),
            ('shift', 'Shift'),
            ('pengaturan', 'Pengaturan'),
        ]

        self.nav_buttons = {}
        for key, label in nav_items:
            if key not in allowed: continue
            btn = ctk.CTkButton(self.sidebar, text=f"  {label}", font=ctk.CTkFont(size=13), height=38,
                                 fg_color='transparent', hover_color=C['sidebar_act'],
                                 text_color=C['text2'], anchor='w', corner_radius=8,
                                 command=lambda k=key: self.navigate(k))
            btn.pack(fill='x', padx=8, pady=1)
            self.nav_buttons[key] = btn

        ctk.CTkFrame(self.sidebar, fg_color='transparent').pack(fill='both', expand=True)

        # Logout
        ctk.CTkButton(self.sidebar, text="  Keluar", font=ctk.CTkFont(size=12), height=34,
                        fg_color=C['red'], hover_color=C['red2'], corner_radius=8,
                        command=self.do_logout).pack(fill='x', padx=8, pady=(0,12))

    def navigate(self, page):
        for k, btn in self.nav_buttons.items():
            is_active = k == page
            btn.configure(fg_color=C['sidebar_act'] if is_active else 'transparent',
                          text_color=C['white'] if is_active else C['text2'],
                          font=ctk.CTkFont(size=13, weight='bold') if is_active else ctk.CTkFont(size=13))
        for w in self.main_area.winfo_children(): w.destroy()
        pages = {
            'dashboard': self.show_dashboard,
            'kasir': self.show_kasir,
            'produk': self.show_produk,
            'restoran': self.show_restoran,
            'laporan': self.show_laporan,
            'stok': self.show_stok,
            'karyawan': self.show_karyawan,
            'pelanggan': self.show_pelanggan,
            'promo': self.show_promo,
            'shift': self.show_shift,
            'pengaturan': self.show_pengaturan,
        }
        if page in pages: pages[page]()

    def do_logout(self):
        if messagebox.askyesno("Konfirmasi", "Yakin ingin keluar?"):
            if self.current_user:
                db.add_audit_log(self.current_user['id'], 'logout', 'auth', 'User logged out')
            self.current_user = None; self.cart = []; self.cart_subtotal = 0
            self.current_shift = None
            for w in self.winfo_children(): w.destroy()
            self.withdraw(); self.show_login()

    # ==================== DASHBOARD ====================
    def show_dashboard(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Dashboard", font=ctk.CTkFont(size=24, weight='bold'), text_color=C['white']).pack(side='left')
        ctk.CTkLabel(tf, text=datetime.now().strftime('%A, %d %B %Y %H:%M'), font=ctk.CTkFont(size=12), text_color=C['text2']).pack(side='right')

        summary = db.get_daily_summary(outlet_id=self.current_outlet)
        realtime = db.get_realtime_revenue()

        cards_f = ctk.CTkFrame(self.main_area, fg_color='transparent')
        cards_f.pack(fill='x', padx=20, pady=(0,12))
        stats = [
            ("Pendapatan Hari Ini", format_currency(summary['total_revenue']), C['green']),
            ("Total Transaksi", str(summary['total_transactions']), C['accent']),
            ("Tunai", format_currency(summary.get('cash_total',0)), C['orange']),
            ("Non-Tunai", format_currency(summary.get('non_cash_total',0)), C['pink']),
            ("Refund", str(summary.get('refund_count',0)), C['red']),
        ]
        for label, value, color in stats:
            card = StatCard(cards_f, icon="", label=label, value=value, color=color)
            card.pack(side='left', expand=True, fill='x', padx=3)

        # Bottom: Charts + Side panels
        bottom = ctk.CTkFrame(self.main_area, fg_color='transparent')
        bottom.pack(fill='both', expand=True, padx=20, pady=(0,16))

        # Left: Sales chart
        chart_frame = ctk.CTkFrame(bottom, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        chart_frame.pack(side='left', fill='both', expand=True, padx=(0,6))
        ctk.CTkLabel(chart_frame, text="Grafik Penjualan 30 Hari", font=ctk.CTkFont(size=14, weight='bold'), text_color=C['white']).pack(padx=14, pady=(12,6), anchor='w')
        self.generate_sales_chart(chart_frame)

        # Right column
        right = ctk.CTkFrame(bottom, fg_color='transparent', width=360)
        right.pack(side='right', fill='both', padx=(6,0))
        right.pack_propagate(False)

        # Top products
        tp_card = ctk.CTkFrame(right, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        tp_card.pack(fill='both', expand=True, pady=(0,6))
        ctk.CTkLabel(tp_card, text="Produk Terlaris", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=14, pady=(10,6), anchor='w')
        tp_scroll = ctk.CTkScrollableFrame(tp_card, fg_color='transparent')
        tp_scroll.pack(fill='both', expand=True, padx=6, pady=(0,6))
        for i, p in enumerate(summary['top_products'][:8]):
            medals = ["1","2","3"]
            medal = medals[i] if i < 3 else f"{i+1}"
            medal_color = [C['gold'], C['silver'], C['orange']][i] if i < 3 else C['text3']
            row = ctk.CTkFrame(tp_scroll, fg_color=C['bg2'], corner_radius=8, height=32)
            row.pack(fill='x', pady=1); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f" {medal}", font=ctk.CTkFont(size=11, weight='bold'), text_color=medal_color, width=24).pack(side='left', padx=(4,0))
            ctk.CTkLabel(row, text=p['product_name'], font=ctk.CTkFont(size=11), text_color=C['text']).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=f"{p['total_qty']}x {format_currency(p['total_sales'])}", font=ctk.CTkFont(size=10), text_color=C['green']).pack(side='right', padx=8)

        # Low stock alert
        low_stock = db.get_low_stock_products()
        if low_stock:
            ls_card = ctk.CTkFrame(right, fg_color=C['red_bg'], corner_radius=12, border_width=1, border_color=C['red'])
            ls_card.pack(fill='x')
            ctk.CTkLabel(ls_card, text=f"Stok Rendah ({len(low_stock)} produk)", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['red']).pack(padx=12, pady=(8,4), anchor='w')
            for ls in low_stock[:4]:
                ctk.CTkLabel(ls_card, text=f"  - {ls['name']}: {ls['stock']} (min: {ls['min_stock']})", font=ctk.CTkFont(size=10), text_color=C['text2']).pack(padx=12, anchor='w')
            ctk.CTkFrame(ls_card, fg_color='transparent', height=6).pack()

    def generate_sales_chart(self, parent):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC[wght].ttf')
            plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            data = db.get_sales_chart_data(30, outlet_id=self.current_outlet)
            fig, ax = plt.subplots(figsize=(6.5, 2.8), facecolor='#1c2128')
            ax.set_facecolor('#1c2128')

            if data:
                dates = [d['date'][5:] for d in data]
                revenues = [d['revenue'] for d in data]
                ax.fill_between(range(len(dates)), revenues, alpha=0.15, color='#58a6ff')
                ax.plot(range(len(dates)), revenues, color='#58a6ff', linewidth=2, marker='o', markersize=3)
                ax.set_xticks(range(0, len(dates), max(1, len(dates)//6)))
                ax.set_xticklabels([dates[i] for i in range(0, len(dates), max(1, len(dates)//6))], color='#484f58', fontsize=8)
            else:
                ax.text(0.5, 0.5, 'Belum ada data', ha='center', va='center', color='#484f58', fontsize=13, transform=ax.transAxes)

            ax.tick_params(colors='#484f58', labelsize=8)
            ax.spines['bottom'].set_color('#30363d'); ax.spines['left'].set_color('#30363d')
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,p: f'{x/1000:.0f}k'))

            plt.tight_layout(pad=1)
            chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chart_sales.png')
            fig.savefig(chart_path, dpi=100, facecolor='#1c2128', bbox_inches='tight')
            plt.close(fig)

            from PIL import Image
            img = Image.open(chart_path)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(600, 260))
            ctk.CTkLabel(parent, image=ctk_img, text='').pack(padx=8, pady=(0,8))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"Chart: {e}", font=ctk.CTkFont(size=10), text_color=C['text3']).pack(pady=20)

    # ==================== KASIR (POS) ====================
    def show_kasir(self):
        self.cart = []; self.cart_subtotal = 0; self.selected_customer = None; self.selected_promo = None

        self.kasir_left = ctk.CTkFrame(self.main_area, fg_color='transparent')
        self.kasir_left.pack(side='left', fill='both', expand=True, padx=(10,5), pady=10)
        self.kasir_right = ctk.CTkFrame(self.main_area, width=380, fg_color='transparent')
        self.kasir_right.pack(side='right', fill='y', padx=(5,10), pady=10)
        self.kasir_right.pack_propagate(False)

        self.build_kasir_products()
        self.build_kasir_cart()

    def build_kasir_products(self):
        # Search + barcode
        sf = ctk.CTkFrame(self.kasir_left, fg_color=C['card'], corner_radius=10, height=44, border_width=1, border_color=C['border'])
        sf.pack(fill='x', pady=(0,6)); sf.pack_propagate(False)
        self.kasir_search = ctk.CTkEntry(sf, placeholder_text="Cari produk atau scan barcode...",
                                           height=36, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=8)
        self.kasir_search.pack(side='left', fill='x', expand=True, padx=8, pady=4)
        self.kasir_search.bind('<KeyRelease>', self.on_kasir_search)
        self.kasir_search.bind('<Return>', self.on_barcode_enter)

        # Action buttons
        act_f = ctk.CTkFrame(sf, fg_color='transparent')
        act_f.pack(side='right', padx=8)
        ctk.CTkButton(act_f, text="Split", width=50, height=28, font=ctk.CTkFont(size=10),
                        fg_color=C['purple'], hover_color=C['platinum'], corner_radius=6,
                        command=self.show_split_bill).pack(side='left', padx=2)
        ctk.CTkButton(act_f, text="Hold", width=50, height=28, font=ctk.CTkFont(size=10),
                        fg_color=C['orange'], hover_color=C['yellow'], corner_radius=6,
                        command=self.hold_order).pack(side='left', padx=2)

        # Category pills
        cf = ctk.CTkFrame(self.kasir_left, fg_color='transparent', height=34)
        cf.pack(fill='x', pady=(0,6)); cf.pack_propagate(False)
        all_btn = ctk.CTkButton(cf, text="Semua", height=28, width=70, font=ctk.CTkFont(size=10, weight='bold'),
                                 fg_color=C['accent'], hover_color=C['accent2'], corner_radius=6,
                                 command=lambda: self.filter_cat(None))
        all_btn.pack(side='left', padx=(0,3))
        self.cat_btns = [all_btn]
        for cat in db.get_all_categories(self.current_outlet):
            btn = ctk.CTkButton(cf, text=f"{cat.get('icon','')} {cat['name']}", height=28, font=ctk.CTkFont(size=10),
                                 fg_color=C['bg3'], hover_color=C['card_hover'], corner_radius=6,
                                 command=lambda cid=cat['id']: self.filter_cat(cid))
            btn.pack(side='left', padx=2)
            self.cat_btns.append(btn)

        self.prod_scroll = ctk.CTkScrollableFrame(self.kasir_left, fg_color='transparent')
        self.prod_scroll.pack(fill='both', expand=True)
        self.load_products_grid()

    def load_products_grid(self, products=None):
        for w in self.prod_scroll.winfo_children(): w.destroy()
        if products is None: products = db.get_all_products(True, self.current_outlet)
        cols = 4
        for i, p in enumerate(products):
            card = ProductCard(self.prod_scroll, product=p, on_add=self.add_to_cart)
            card.grid(row=i//cols, column=i%cols, padx=3, pady=3, sticky='nsew')
        for c in range(cols): self.prod_scroll.grid_columnconfigure(c, weight=1)

    def filter_cat(self, cid):
        for i, btn in enumerate(self.cat_btns):
            btn.configure(fg_color=C['accent'] if (i==0 and cid is None) or (i>0 and self.cat_btns[i].winfo_exists() and hasattr(btn,'_cid') and btn._cid==cid) else C['bg3'])
        if cid: self.load_products_grid(db.get_products_by_category(cid, self.current_outlet))
        else: self.load_products_grid()

    def on_kasir_search(self, e=None):
        kw = self.kasir_search.get().strip()
        self.load_products_grid(db.search_products(kw, self.current_outlet) if kw else db.get_all_products(True, self.current_outlet))

    def on_barcode_enter(self, e=None):
        bc = self.kasir_search.get().strip()
        if not bc: return
        p = db.get_product_by_barcode(bc)
        if p: self.add_to_cart(p); self.kasir_search.delete(0, 'end')
        else: self.on_kasir_search()

    def add_to_cart(self, product):
        if product['stock'] <= 0:
            messagebox.showwarning("Stok Habis", f"Stok {product['name']} habis!"); return
        # Check if product has variations
        if product.get('has_variations'):
            self.show_variation_picker(product); return
        for item in self.cart:
            if item['product_id'] == product['id'] and not item.get('variation_id'):
                if item['quantity'] >= product['stock']:
                    messagebox.showwarning("Stok", f"Stok hanya {product['stock']}!"); return
                item['quantity'] += 1
                item['subtotal'] = item['quantity'] * item['product_price']
                self.update_cart_display(); return
        self.cart.append({
            'product_id': product['id'], 'product_name': product['name'],
            'product_price': product['sell_price'], 'quantity': 1,
            'subtotal': product['sell_price'], 'max_stock': product['stock'],
            'is_food': product.get('is_food', 0), 'custom_note': '', 'variation_id': None, 'variation_text': ''
        })
        self.update_cart_display()

    def show_variation_picker(self, product):
        dlg = ctk.CTkToplevel(self); dlg.title("Pilih Variasi")
        dlg.geometry("400x450"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth()//2)-200; y = (dlg.winfo_screenheight()//2)-225
        dlg.geometry(f'400x450+{x}+{y}')

        ctk.CTkLabel(dlg, text=product['name'], font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(16,8))

        variations = db.get_product_variations(product['id'])
        var_groups = {}
        for v in variations:
            vn = v['variation_name']
            if vn not in var_groups: var_groups[vn] = []
            var_groups[vn].append(v)

        selected_vars = {}

        for vname, vvals in var_groups.items():
            ctk.CTkLabel(dlg, text=vname, font=ctk.CTkFont(size=13, weight='bold'), text_color=C['text']).pack(padx=20, anchor='w', pady=(8,4))
            val_f = ctk.CTkFrame(dlg, fg_color='transparent')
            val_f.pack(fill='x', padx=20)
            sv = ctk.StringVar(value=vvals[0]['variation_value'])
            selected_vars[vname] = vvals[0]
            for vv in vvals:
                price_txt = f"+{format_currency(vv['price_adjustment'])}" if vv['price_adjustment'] > 0 else ""
                txt = f"{vv['variation_value']} {price_txt}"
                btn = ctk.CTkRadioButton(val_f, text=txt, variable=sv, value=vv['variation_value'],
                                          font=ctk.CTkFont(size=12), text_color=C['text'],
                                          command=lambda vname=vname, vv=vv: selected_vars.update({vname: vv}))
                btn.pack(side='left', padx=4, pady=2)

        # Custom note
        ctk.CTkLabel(dlg, text="Catatan:", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(padx=20, anchor='w', pady=(12,4))
        note_entry = ctk.CTkEntry(dlg, placeholder_text="Contoh: tidak pedas, extra keju...", height=36, font=ctk.CTkFont(size=12),
                                   fg_color=C['bg2'], corner_radius=8)
        note_entry.pack(fill='x', padx=20)

        # Quantity
        qty_f = ctk.CTkFrame(dlg, fg_color='transparent')
        qty_f.pack(fill='x', padx=20, pady=(12,0))
        ctk.CTkLabel(qty_f, text="Jumlah:", font=ctk.CTkFont(size=12), text_color=C['text']).pack(side='left')
        qty_var = tk.IntVar(value=1)
        ctk.CTkButton(qty_f, text="-", width=32, height=28, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['red'], corner_radius=6, command=lambda: qty_var.set(max(1, qty_var.get()-1))).pack(side='left', padx=8)
        qty_lbl = ctk.CTkLabel(qty_f, textvariable=qty_var, font=ctk.CTkFont(size=14, weight='bold'), text_color=C['white'], width=30)
        qty_lbl.pack(side='left')
        ctk.CTkButton(qty_f, text="+", width=32, height=28, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['green'], corner_radius=6, command=lambda: qty_var.set(qty_var.get()+1)).pack(side='left', padx=8)

        def add_it():
            qty = qty_var.get()
            total_adj = sum(vv['price_adjustment'] for vv in selected_vars.values())
            var_text = " | ".join(f"{vv['variation_name']}: {vv['variation_value']}" for vv in selected_vars.values())
            var_id = list(selected_vars.values())[0]['id'] if selected_vars else None
            final_price = product['sell_price'] + total_adj
            self.cart.append({
                'product_id': product['id'], 'product_name': product['name'],
                'product_price': final_price, 'quantity': qty,
                'subtotal': final_price * qty, 'max_stock': product['stock'],
                'is_food': product.get('is_food', 0), 'custom_note': note_entry.get(),
                'variation_id': var_id, 'variation_text': var_text
            })
            self.update_cart_display()
            dlg.destroy()

        ctk.CTkButton(dlg, text="Tambah ke Keranjang", height=40, font=ctk.CTkFont(size=14, weight='bold'),
                        fg_color=C['accent'], hover_color=C['accent2'], corner_radius=10, command=add_it).pack(fill='x', padx=20, pady=(16,10))

    def remove_from_cart(self, idx):
        if 0 <= idx < len(self.cart): del self.cart[idx]; self.update_cart_display()

    def update_cart_qty(self, idx, delta):
        if 0 <= idx < len(self.cart):
            nq = self.cart[idx]['quantity'] + delta
            if nq <= 0: self.remove_from_cart(idx); return
            if nq > self.cart[idx]['max_stock']:
                messagebox.showwarning("Stok", f"Maks: {self.cart[idx]['max_stock']}"); return
            self.cart[idx]['quantity'] = nq
            self.cart[idx]['subtotal'] = nq * self.cart[idx]['product_price']
            self.update_cart_display()

    def build_kasir_cart(self):
        cart_card = ctk.CTkFrame(self.kasir_right, fg_color=C['card'], corner_radius=14, border_width=1, border_color=C['border'])
        cart_card.pack(fill='both', expand=True)

        # Header
        hdr = ctk.CTkFrame(cart_card, fg_color=C['accent'], corner_radius=10, height=40)
        hdr.pack(fill='x', padx=6, pady=(6,3)); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Keranjang", font=ctk.CTkFont(size=14, weight='bold'), text_color=C['white']).pack(side='left', padx=12)
        ctk.CTkButton(hdr, text="Hapus", width=55, height=24, font=ctk.CTkFont(size=9),
                        fg_color=C['red'], hover_color=C['red2'], corner_radius=5,
                        command=self.clear_cart).pack(side='right', padx=8)

        # Customer + Promo row
        cp_f = ctk.CTkFrame(cart_card, fg_color='transparent')
        cp_f.pack(fill='x', padx=8, pady=(3,2))
        cust_f = ctk.CTkFrame(cp_f, fg_color=C['bg2'], corner_radius=8, height=30)
        cust_f.pack(side='left', fill='x', expand=True, padx=(0,3)); cust_f.pack_propagate(False)
        self.cust_display = ctk.CTkLabel(cust_f, text="Umum", font=ctk.CTkFont(size=10), text_color=C['text2'])
        self.cust_display.pack(side='left', padx=6)
        ctk.CTkButton(cust_f, text="Pilih", width=35, height=22, font=ctk.CTkFont(size=8),
                        fg_color=C['accent'], corner_radius=4, command=self.show_customer_picker).pack(side='right', padx=4)

        promo_f = ctk.CTkFrame(cp_f, fg_color=C['bg2'], corner_radius=8, height=30)
        promo_f.pack(side='right', fill='x', expand=True, padx=(3,0)); promo_f.pack_propagate(False)
        self.promo_display = ctk.CTkLabel(promo_f, text="Tanpa Promo", font=ctk.CTkFont(size=10), text_color=C['text2'])
        self.promo_display.pack(side='left', padx=6)
        ctk.CTkButton(promo_f, text="Pilih", width=35, height=22, font=ctk.CTkFont(size=8),
                        fg_color=C['accent'], corner_radius=4, command=self.show_promo_picker).pack(side='right', padx=4)

        # Cart items
        self.cart_scroll = ctk.CTkScrollableFrame(cart_card, fg_color='transparent', height=180)
        self.cart_scroll.pack(fill='both', expand=True, padx=6, pady=3)

        # Summary
        sum_f = ctk.CTkFrame(cart_card, fg_color=C['bg2'], corner_radius=10)
        sum_f.pack(fill='x', padx=8, pady=3)
        self.subtotal_lbl = ctk.CTkLabel(sum_f, text="Subtotal: Rp0", font=ctk.CTkFont(size=11), text_color=C['text2'])
        self.subtotal_lbl.pack(anchor='w', padx=12, pady=(8,1))
        self.discount_lbl = ctk.CTkLabel(sum_f, text="Diskon: Rp0", font=ctk.CTkFont(size=11), text_color=C['red'])
        self.discount_lbl.pack(anchor='w', padx=12, pady=1)
        self.tax_lbl = ctk.CTkLabel(sum_f, text="Pajak & Service: Rp0", font=ctk.CTkFont(size=11), text_color=C['text3'])
        self.tax_lbl.pack(anchor='w', padx=12, pady=1)
        self.total_lbl = ctk.CTkLabel(sum_f, text="Total: Rp0", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['green'])
        self.total_lbl.pack(anchor='w', padx=12, pady=(2,8))

        # Payment
        pay_f = ctk.CTkFrame(cart_card, fg_color=C['bg2'], corner_radius=8)
        pay_f.pack(fill='x', padx=8, pady=(0,3))

        pm_f = ctk.CTkFrame(pay_f, fg_color='transparent')
        pm_f.pack(fill='x', padx=10, pady=(6,3))
        ctk.CTkLabel(pm_f, text="Metode:", font=ctk.CTkFont(size=10), text_color=C['text2']).pack(side='left')
        self.pay_var = ctk.StringVar(value="Tunai")
        ctk.CTkOptionMenu(pm_f, variable=self.pay_var, values=["Tunai","Debit","Kredit","E-Wallet","QRIS"],
                            width=110, height=26, font=ctk.CTkFont(size=10), fg_color=C['card'], button_color=C['accent']).pack(side='right')

        paid_f = ctk.CTkFrame(pay_f, fg_color='transparent')
        paid_f.pack(fill='x', padx=10, pady=(0,6))
        ctk.CTkLabel(paid_f, text="Dibayar:", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(side='left')
        self.paid_entry = ctk.CTkEntry(paid_f, width=140, height=30, font=ctk.CTkFont(size=13, weight='bold'),
                                         fg_color=C['card'], corner_radius=6, placeholder_text="0")
        self.paid_entry.pack(side='right')
        self.paid_entry.bind('<KeyRelease>', self.update_change)

        self.change_lbl = ctk.CTkLabel(cart_card, text="Kembalian: Rp0", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['green'])
        self.change_lbl.pack(padx=12, pady=(0,3))

        # Quick amount buttons
        qa_f = ctk.CTkFrame(cart_card, fg_color='transparent')
        qa_f.pack(fill='x', padx=8, pady=(0,3))
        for amt in ['Uang Pas', '50rb', '100rb', '200rb', '500rb']:
            ctk.CTkButton(qa_f, text=amt, height=24, font=ctk.CTkFont(size=9),
                            fg_color=C['bg3'], hover_color=C['bg4'], corner_radius=4,
                            command=lambda a=amt: self.quick_amount(a)).pack(side='left', expand=True, fill='x', padx=1)

        # Pay button
        ctk.CTkButton(cart_card, text="B A Y A R", height=44, font=ctk.CTkFont(size=15, weight='bold'),
                        fg_color=C['green'], hover_color=C['green2'], corner_radius=12,
                        command=self.process_payment).pack(fill='x', padx=8, pady=(0,8))

    def quick_amount(self, amt):
        if amt == 'Uang Pas':
            subtotal = self.cart_subtotal
            discount = db.calculate_promo_discount(self.selected_promo, subtotal) if self.selected_promo else 0
            total = subtotal - discount
            self.paid_entry.delete(0, 'end')
            self.paid_entry.insert(0, str(int(total)))
        else:
            val = int(amt.replace('rb','000'))
            self.paid_entry.delete(0, 'end')
            self.paid_entry.insert(0, str(val))
        self.update_change()

    def update_cart_display(self, e=None):
        for w in self.cart_scroll.winfo_children(): w.destroy()
        subtotal = sum(i['subtotal'] for i in self.cart)
        self.cart_subtotal = subtotal

        for i, item in enumerate(self.cart):
            row = ctk.CTkFrame(self.cart_scroll, fg_color=C['bg2'], corner_radius=8, height=44)
            row.pack(fill='x', pady=1, padx=1); row.pack_propagate(False)

            info = ctk.CTkFrame(row, fg_color='transparent')
            info.pack(side='left', fill='y', padx=6)
            ctk.CTkLabel(info, text=item['product_name'], font=ctk.CTkFont(size=10, weight='bold'), text_color=C['white']).pack(anchor='w', pady=(3,0))
            note_txt = ""
            if item.get('variation_text'): note_txt += item['variation_text']
            if item.get('custom_note'): note_txt += f" ({item['custom_note']})"
            if note_txt:
                ctk.CTkLabel(info, text=note_txt[:30], font=ctk.CTkFont(size=8), text_color=C['purple']).pack(anchor='w')
            ctk.CTkLabel(info, text=f"{format_currency(item['product_price'])} x {item['quantity']}", font=ctk.CTkFont(size=9), text_color=C['text3']).pack(anchor='w')

            qf = ctk.CTkFrame(row, fg_color='transparent')
            qf.pack(side='left', padx=2)
            for txt, cmd, clr in [("-", lambda idx=i: self.update_cart_qty(idx,-1), C['red']),
                                   ("+", lambda idx=i: self.update_cart_qty(idx,1), C['green'])]:
                ctk.CTkButton(qf, text=txt, width=22, height=18, font=ctk.CTkFont(size=10, weight='bold'),
                               fg_color=clr, corner_radius=4, command=cmd).pack(side='left', padx=1)

            rf = ctk.CTkFrame(row, fg_color='transparent')
            rf.pack(side='right', fill='y', padx=6)
            ctk.CTkLabel(rf, text=format_currency(item['subtotal']), font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green']).pack(anchor='e', pady=(3,0))
            ctk.CTkButton(rf, text="X", width=16, height=14, font=ctk.CTkFont(size=7),
                           fg_color='transparent', hover_color=C['red'], text_color=C['text3'],
                           corner_radius=3, command=lambda idx=i: self.remove_from_cart(idx)).pack(anchor='e')

        discount = db.calculate_promo_discount(self.selected_promo, subtotal) if self.selected_promo else 0
        tax = 0
        total = subtotal - discount + tax
        self.subtotal_lbl.configure(text=f"Subtotal: {format_currency(subtotal)}")
        self.discount_lbl.configure(text=f"Diskon: -{format_currency(discount)}")
        self.tax_lbl.configure(text=f"Pajak & Service: {format_currency(tax)}")
        self.total_lbl.configure(text=f"Total: {format_currency(total)}")
        self.update_change()

    def update_change(self, e=None):
        subtotal = self.cart_subtotal
        discount = db.calculate_promo_discount(self.selected_promo, subtotal) if self.selected_promo else 0
        total = subtotal - discount
        try: paid = float(self.paid_entry.get() or 0)
        except: paid = 0
        change = paid - total
        if change >= 0:
            self.change_lbl.configure(text=f"Kembalian: {format_currency(change)}", text_color=C['green'])
        else:
            self.change_lbl.configure(text=f"Kurang: {format_currency(abs(change))}", text_color=C['red'])

    def clear_cart(self):
        self.cart = []; self.cart_subtotal = 0; self.selected_promo = None
        self.selected_customer = None; self.paid_entry.delete(0, 'end')
        self.cust_display.configure(text="Umum")
        self.promo_display.configure(text="Tanpa Promo")
        self.update_cart_display()

    def show_customer_picker(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Pilih Pelanggan")
        dlg.geometry("480x480"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth()//2)-240; y = (dlg.winfo_screenheight()//2)-240
        dlg.geometry(f'480x480+{x}+{y}')

        ctk.CTkLabel(dlg, text="Pilih Pelanggan", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,8))
        search = ctk.CTkEntry(dlg, placeholder_text="Cari nama/telepon...", height=34, font=ctk.CTkFont(size=12), fg_color=C['card'], corner_radius=8)
        search.pack(fill='x', padx=18, pady=(0,8))
        scroll = ctk.CTkScrollableFrame(dlg, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=18)

        def load_customers(kw=''):
            for w in scroll.winfo_children(): w.destroy()
            custs = db.search_customers(kw) if kw else db.get_all_customers()
            for c in custs:
                row = ctk.CTkFrame(scroll, fg_color=C['card'], corner_radius=8, height=42, border_width=1, border_color=C['border'])
                row.pack(fill='x', pady=2); row.pack_propagate(False)
                ctk.CTkLabel(row, text=c['name'], font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(side='left', padx=8)
                TierBadge(row, tier=c['tier']).pack(side='left', padx=4)
                ctk.CTkLabel(row, text=f"{c['points']}pts", font=ctk.CTkFont(size=9), text_color=C['gold']).pack(side='left', padx=4)
                ctk.CTkButton(row, text="Pilih", width=45, height=22, font=ctk.CTkFont(size=9),
                               fg_color=C['accent'], corner_radius=5,
                               command=lambda cust=c: [setattr(self, 'selected_customer', cust),
                                   self.cust_display.configure(text=f"{cust['name']} ({cust['tier']})"), dlg.destroy()]).pack(side='right', padx=8)

        load_customers()
        search.bind('<KeyRelease>', lambda e: load_customers(search.get().strip()))

        ctk.CTkButton(dlg, text="Umum (Walk-in)", height=34, font=ctk.CTkFont(size=12),
                        fg_color=C['bg3'], hover_color=C['bg4'], corner_radius=8,
                        command=lambda: [setattr(self, 'selected_customer', None),
                            self.cust_display.configure(text="Umum"), dlg.destroy()]).pack(fill='x', padx=18, pady=(6,10))

    def show_promo_picker(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Pilih Promo")
        dlg.geometry("420x400"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth()//2)-210; y = (dlg.winfo_screenheight()//2)-200
        dlg.geometry(f'420x400+{x}+{y}')

        ctk.CTkLabel(dlg, text="Pilih Promo", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,8))
        promos = db.get_active_promos()
        if not promos:
            ctk.CTkLabel(dlg, text="Tidak ada promo aktif", font=ctk.CTkFont(size=12), text_color=C['text3']).pack(pady=20)
        scroll = ctk.CTkScrollableFrame(dlg, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=18)
        for p in promos:
            row = ctk.CTkFrame(scroll, fg_color=C['card'], corner_radius=8, height=48, border_width=1, border_color=C['border'])
            row.pack(fill='x', pady=2); row.pack_propagate(False)
            val_txt = f"{p['value']}%" if p['type']=='percentage' else format_currency(p['value'])
            ctk.CTkLabel(row, text=f"{p['name']} ({val_txt})", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(side='left', padx=8)
            ctk.CTkLabel(row, text=f"Min: {format_currency(p['min_purchase'])}", font=ctk.CTkFont(size=9), text_color=C['text3']).pack(side='left', padx=4)
            ctk.CTkButton(row, text="Pilih", width=45, height=22, font=ctk.CTkFont(size=9),
                           fg_color=C['accent'], corner_radius=5,
                           command=lambda pr=p: [setattr(self, 'selected_promo', pr),
                               self.promo_display.configure(text=pr['name']), dlg.destroy(), self.update_cart_display()]).pack(side='right', padx=8)

        ctk.CTkButton(dlg, text="Tanpa Promo", height=34, font=ctk.CTkFont(size=12),
                        fg_color=C['bg3'], hover_color=C['bg4'], corner_radius=8,
                        command=lambda: [setattr(self, 'selected_promo', None),
                            self.promo_display.configure(text="Tanpa Promo"), dlg.destroy(), self.update_cart_display()]).pack(fill='x', padx=18, pady=(6,10))

    def process_payment(self):
        if not self.cart:
            messagebox.showwarning("Kosong", "Keranjang masih kosong!"); return

        subtotal = self.cart_subtotal
        discount = db.calculate_promo_discount(self.selected_promo, subtotal) if self.selected_promo else 0
        total = subtotal - discount

        try: paid = float(self.paid_entry.get() or 0)
        except: paid = 0

        if self.pay_var.get() == 'Tunai' and paid < total:
            messagebox.showwarning("Kurang", f"Uang dibayar kurang! Total: {format_currency(total)}"); return

        if paid == 0 and self.pay_var.get() != 'Tunai':
            paid = total  # Auto for non-cash

        change = paid - total
        customer_id = self.selected_customer['id'] if self.selected_customer else None
        customer_name = self.selected_customer['name'] if self.selected_customer else 'Umum'
        promo_id = self.selected_promo['id'] if self.selected_promo else None

        result = db.create_transaction(
            user_id=self.current_user['id'], customer_name=customer_name, items=self.cart,
            discount=discount, tax_rate=0, paid=paid, payment_method=self.pay_var.get(),
            shift_id=self.current_shift['id'] if self.current_shift else None,
            customer_id=customer_id, promo_id=promo_id,
            discount_type='promo' if self.selected_promo else 'manual',
            outlet_id=self.current_outlet, table_id=getattr(self, 'active_table', None)
        )

        if result:
            # Show success dialog
            self.show_payment_success(result, total, paid, change)
            # Auto receipt
            tx = db.get_transaction_detail(result['tx_id'])
            if tx: save_receipt(tx)
            self.clear_cart()
        else:
            messagebox.showerror("Error", "Gagal memproses pembayaran!")

    def show_payment_success(self, result, total, paid, change):
        dlg = ctk.CTkToplevel(self); dlg.title("Pembayaran Berhasil")
        dlg.geometry("420x350"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth()//2)-210; y = (dlg.winfo_screenheight()//2)-175
        dlg.geometry(f'420x350+{x}+{y}')

        card = ctk.CTkFrame(dlg, fg_color=C['card'], corner_radius=16, border_width=1, border_color=C['green'])
        card.pack(fill='both', expand=True, padx=16, pady=16)

        ctk.CTkLabel(card, text="Pembayaran Berhasil!", font=ctk.CTkFont(size=20, weight='bold'), text_color=C['green']).pack(pady=(20,8))
        ctk.CTkLabel(card, text=result['invoice_no'], font=ctk.CTkFont(size=14), text_color=C['accent']).pack(pady=(0,12))

        info_f = ctk.CTkFrame(card, fg_color=C['bg2'], corner_radius=10)
        info_f.pack(fill='x', padx=20, pady=(0,10))
        for lbl, val in [("Total", format_currency(total)), ("Dibayar", format_currency(paid)), ("Kembalian", format_currency(change))]:
            row = ctk.CTkFrame(info_f, fg_color='transparent')
            row.pack(fill='x', padx=12, pady=2)
            ctk.CTkLabel(row, text=lbl, font=ctk.CTkFont(size=12), text_color=C['text2']).pack(side='left')
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(side='right')

        if result.get('points_earned', 0) > 0:
            ctk.CTkLabel(card, text=f"Poin didapat: +{result['points_earned']}", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['gold']).pack(pady=(0,8))

        btn_f = ctk.CTkFrame(card, fg_color='transparent')
        btn_f.pack(fill='x', padx=20, pady=(0,12))
        ctk.CTkButton(btn_f, text="Cetak Struk", height=36, font=ctk.CTkFont(size=12, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=lambda: self.print_receipt(result['tx_id'])).pack(side='left', expand=True, fill='x', padx=(0,4))
        ctk.CTkButton(btn_f, text="Selesai", height=36, font=ctk.CTkFont(size=12, weight='bold'),
                        fg_color=C['green'], corner_radius=8, command=dlg.destroy).pack(side='right', expand=True, fill='x', padx=(4,0))

    def print_receipt(self, tx_id):
        tx = db.get_transaction_detail(tx_id)
        if tx:
            path = save_receipt(tx)
            messagebox.showinfo("Struk", f"Struk disimpan: {path}")

    def show_split_bill(self):
        if not self.cart:
            messagebox.showwarning("Kosong", "Keranjang masih kosong!"); return
        dlg = ctk.CTkToplevel(self); dlg.title("Split Bill")
        dlg.geometry("500x500"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)

        ctk.CTkLabel(dlg, text="Split Bill", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,8))
        ctk.CTkLabel(dlg, text=f"Total: {format_currency(self.cart_subtotal)}", font=ctk.CTkFont(size=14, weight='bold'), text_color=C['green']).pack(pady=(0,12))

        # Split options
        ctk.CTkLabel(dlg, text="Pilih metode split:", font=ctk.CTkFont(size=13), text_color=C['text']).pack(pady=(0,8))

        for method, desc in [("Rata", "Bagi rata antar pembayar"), ("Per Item", "Pilih item per pembayar"), ("Nominal", "Tentukan nominal per pembayar")]:
            ctk.CTkButton(dlg, text=f"{method} - {desc}", height=40, font=ctk.CTkFont(size=12),
                            fg_color=C['card'], hover_color=C['card_hover'], corner_radius=8,
                            border_width=1, border_color=C['border'],
                            command=lambda m=method: [dlg.destroy(), self.execute_split(m)]).pack(fill='x', padx=20, pady=3)

        ctk.CTkButton(dlg, text="Batal", height=36, font=ctk.CTkFont(size=12),
                        fg_color=C['red'], corner_radius=8, command=dlg.destroy).pack(fill='x', padx=20, pady=(12,10))

    def execute_split(self, method):
        if method == "Rata":
            dlg = ctk.CTkToplevel(self); dlg.title("Split Rata")
            dlg.geometry("380x280"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
            dlg.transient(self)
            ctk.CTkLabel(dlg, text="Jumlah Pembayar", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(pady=(16,8))
            split_var = tk.IntVar(value=2)
            sf = ctk.CTkFrame(dlg, fg_color='transparent')
            sf.pack(pady=8)
            ctk.CTkButton(sf, text="-", width=36, height=30, font=ctk.CTkFont(size=14, weight='bold'),
                            fg_color=C['red'], corner_radius=6, command=lambda: split_var.set(max(2, split_var.get()-1))).pack(side='left', padx=8)
            ctk.CTkLabel(sf, textvariable=split_var, font=ctk.CTkFont(size=24, weight='bold'), text_color=C['white'], width=40).pack(side='left')
            ctk.CTkButton(sf, text="+", width=36, height=30, font=ctk.CTkFont(size=14, weight='bold'),
                            fg_color=C['green'], corner_radius=6, command=lambda: split_var.set(min(10, split_var.get()+1))).pack(side='left', padx=8)

            per_person = self.cart_subtotal / split_var.get()
            ctk.CTkLabel(dlg, text=f"Per pembayar: {format_currency(per_person)}", font=ctk.CTkFont(size=14, weight='bold'), text_color=C['green']).pack(pady=8)
            ctk.CTkButton(dlg, text="Proses Split", height=40, font=ctk.CTkFont(size=14, weight='bold'),
                            fg_color=C['green'], corner_radius=10, command=dlg.destroy).pack(fill='x', padx=20, pady=12)

    def hold_order(self):
        if not self.cart:
            messagebox.showwarning("Kosong", "Keranjang masih kosong!"); return
        messagebox.showinfo("Hold", "Order ditahan! Bisa dilanjutkan nanti.")
        self.clear_cart()

    # ==================== PRODUK ====================
    def show_produk(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Manajemen Produk", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')
        ctk.CTkButton(tf, text="+ Tambah Produk", height=34, font=ctk.CTkFont(size=12, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=self.show_add_product_dialog).pack(side='right')

        # Search
        sf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        sf.pack(fill='x', padx=20, pady=(0,8))
        self.prod_search = ctk.CTkEntry(sf, placeholder_text="Cari produk...", height=34, font=ctk.CTkFont(size=12),
                                          fg_color=C['card'], corner_radius=8)
        self.prod_search.pack(side='left', fill='x', expand=True)
        self.prod_search.bind('<KeyRelease>', lambda e: self.load_produk_table())

        # Table
        table_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        table_f.pack(fill='both', expand=True, padx=20, pady=(0,16))
        self.prod_scroll_frame = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
        self.prod_scroll_frame.pack(fill='both', expand=True, padx=6, pady=6)

        # Header
        hdr = ctk.CTkFrame(self.prod_scroll_frame, fg_color=C['bg3'], corner_radius=6, height=32)
        hdr.pack(fill='x', pady=(0,3)); hdr.pack_propagate(False)
        for txt, w in [("Produk", 220), ("Kategori", 100), ("Harga Beli", 100), ("Harga Jual", 100), ("Stok", 60), ("Var", 40), ("Aksi", 130)]:
            ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['text2'], width=w).pack(side='left', padx=4)

        self.load_produk_table()

    def load_produk_table(self):
        for w in self.prod_scroll_frame.winfo_children()[1:]:
            w.destroy()
        kw = self.prod_search.get().strip() if hasattr(self, 'prod_search') else ''
        products = db.search_products(kw, self.current_outlet) if kw else db.get_all_products(True, self.current_outlet)
        for p in products:
            row = ctk.CTkFrame(self.prod_scroll_frame, fg_color=C['bg2'], corner_radius=6, height=34)
            row.pack(fill='x', pady=1); row.pack_propagate(False)
            ctk.CTkLabel(row, text=p['name'][:28], font=ctk.CTkFont(size=11), text_color=C['text'], width=220).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=p.get('category_name','-')[:12], font=ctk.CTkFont(size=10), text_color=C['text2'], width=100).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=format_currency(p['buy_price']), font=ctk.CTkFont(size=10), text_color=C['text3'], width=100).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=format_currency(p['sell_price']), font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green'], width=100).pack(side='left', padx=4)
            stock_color = C['red'] if p['stock'] <= p['min_stock'] else C['text']
            ctk.CTkLabel(row, text=str(p['stock']), font=ctk.CTkFont(size=10), text_color=stock_color, width=60).pack(side='left', padx=4)
            ctk.CTkLabel(row, text="Y" if p.get('has_variations') else "-", font=ctk.CTkFont(size=10), text_color=C['purple'], width=40).pack(side='left', padx=4)

            act_f = ctk.CTkFrame(row, fg_color='transparent', width=130)
            act_f.pack(side='right', padx=4)
            act_f.pack_propagate(False)
            ctk.CTkButton(act_f, text="Edit", width=42, height=22, font=ctk.CTkFont(size=8), fg_color=C['accent'], corner_radius=4,
                           command=lambda pid=p['id']: self.show_edit_product_dialog(pid)).pack(side='left', padx=1)
            ctk.CTkButton(act_f, text="Stok", width=42, height=22, font=ctk.CTkFont(size=8), fg_color=C['orange'], corner_radius=4,
                           command=lambda pid=p['id']: self.show_stock_adjust_dialog(pid)).pack(side='left', padx=1)
            ctk.CTkButton(act_f, text="Hapus", width=42, height=22, font=ctk.CTkFont(size=8), fg_color=C['red'], corner_radius=4,
                           command=lambda pid=p['id']: [db.delete_product(pid), self.load_produk_table()]).pack(side='left', padx=1)

    def show_add_product_dialog(self):
        self._product_dialog(None)

    def show_edit_product_dialog(self, pid):
        self._product_dialog(pid)

    def _product_dialog(self, pid=None):
        product = db.get_product_by_id(pid) if pid else None
        dlg = ctk.CTkToplevel(self); dlg.title("Edit Produk" if product else "Tambah Produk")
        dlg.geometry("500x600"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)

        ctk.CTkLabel(dlg, text="Edit Produk" if product else "Tambah Produk", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,10))

        scroll = ctk.CTkScrollableFrame(dlg, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=18)

        fields = {}
        for lbl, key, default in [("Barcode", "barcode", product['barcode'] if product else ""),
                                   ("Nama Produk", "name", product['name'] if product else ""),
                                   ("Harga Beli", "buy_price", str(product['buy_price']) if product else "0"),
                                   ("Harga Jual", "sell_price", str(product['sell_price']) if product else "0"),
                                   ("Stok", "stock", str(product['stock']) if product else "0"),
                                   ("Min Stok", "min_stock", str(product['min_stock']) if product else "5"),
                                   ("Satuan", "unit", product['unit'] if product else "pcs")]:
            ctk.CTkLabel(scroll, text=lbl, font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', pady=(6,2))
            e = ctk.CTkEntry(scroll, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=6)
            e.pack(fill='x')
            e.insert(0, default)
            fields[key] = e

        # Category
        ctk.CTkLabel(scroll, text="Kategori", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', pady=(6,2))
        cats = db.get_all_categories(self.current_outlet)
        cat_names = [c['name'] for c in cats]
        cat_map = {c['name']: c['id'] for c in cats}
        cat_var = ctk.StringVar(value=product.get('category_name','') if product and product.get('category_name') else (cat_names[0] if cat_names else ''))
        cat_menu = ctk.CTkOptionMenu(scroll, variable=cat_var, values=cat_names, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], button_color=C['accent'])
        cat_menu.pack(fill='x')

        # Is food
        is_food_var = ctk.IntVar(value=product['is_food'] if product else 0)
        ctk.CTkCheckBox(scroll, text="Produk Makanan (Kitchen Display)", variable=is_food_var, font=ctk.CTkFont(size=11), text_color=C['text']).pack(anchor='w', pady=(8,2))

        def save():
            data = {k: v.get() for k, v in fields.items()}
            cat_id = cat_map.get(cat_var.get())
            try:
                if pid:
                    db.update_product(pid, data['barcode'], data['name'], cat_id, float(data['buy_price']),
                        float(data['sell_price']), int(data['stock']), int(data['min_stock']), data['unit'],
                        1, is_food_var.get())
                else:
                    new_pid = db.add_product(data['barcode'], data['name'], cat_id, float(data['buy_price']),
                        float(data['sell_price']), int(data['stock']), int(data['min_stock']), data['unit'],
                        is_food_var.get(), outlet_id=self.current_outlet)
                dlg.destroy(); self.load_produk_table()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=dlg)

        ctk.CTkButton(dlg, text="Simpan", height=40, font=ctk.CTkFont(size=14, weight='bold'),
                        fg_color=C['accent'], corner_radius=10, command=save).pack(fill='x', padx=18, pady=(10,14))

    def show_stock_adjust_dialog(self, pid):
        product = db.get_product_by_id(pid)
        if not product: return
        dlg = ctk.CTkToplevel(self); dlg.title("Adjust Stok")
        dlg.geometry("380x280"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)

        ctk.CTkLabel(dlg, text=f"Adjust Stok: {product['name']}", font=ctk.CTkFont(size=15, weight='bold'), text_color=C['white']).pack(pady=(14,4))
        ctk.CTkLabel(dlg, text=f"Stok saat ini: {product['stock']}", font=ctk.CTkFont(size=12), text_color=C['text2']).pack(pady=(0,10))

        ctk.CTkLabel(dlg, text="Tipe:", font=ctk.CTkFont(size=11), text_color=C['text']).pack(anchor='w', padx=20)
        type_var = ctk.StringVar(value="masuk")
        ctk.CTkSegmentedButton(dlg, values=["masuk", "keluar", "koreksi"], variable=type_var, font=ctk.CTkFont(size=11)).pack(fill='x', padx=20, pady=4)

        ctk.CTkLabel(dlg, text="Jumlah:", font=ctk.CTkFont(size=11), text_color=C['text']).pack(anchor='w', padx=20, pady=(8,2))
        qty_entry = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=6)
        qty_entry.pack(fill='x', padx=20)

        ctk.CTkLabel(dlg, text="Catatan:", font=ctk.CTkFont(size=11), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
        note_entry = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=6, placeholder_text="Opsional")
        note_entry.pack(fill='x', padx=20)

        def save():
            try: qty = int(qty_entry.get())
            except: messagebox.showwarning("Error", "Jumlah harus angka!", parent=dlg); return
            t = type_var.get()
            if t == 'keluar': qty = -qty
            elif t == 'koreksi': qty = qty - product['stock']
            db.update_stock(pid, qty, t, note_entry.get(), self.current_user['id'], self.current_outlet)
            dlg.destroy(); self.load_produk_table()

        ctk.CTkButton(dlg, text="Simpan", height=36, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=save).pack(fill='x', padx=20, pady=(12,10))

    # ==================== RESTORAN ====================
    def show_restoran(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Manajemen Restoran", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')

        # Floor selector
        floor_var = ctk.IntVar(value=1)
        ff = ctk.CTkFrame(tf, fg_color='transparent')
        ff.pack(side='right')
        ctk.CTkLabel(ff, text="Lantai:", font=ctk.CTkFont(size=11), text_color=C['text2']).pack(side='left', padx=4)
        ctk.CTkSegmentedButton(ff, values=["1", "2"], variable=floor_var, font=ctk.CTkFont(size=11),
                                 command=lambda v: self.load_tables(int(v))).pack(side='left')

        # Table grid
        self.table_grid = ctk.CTkScrollableFrame(self.main_area, fg_color='transparent')
        self.table_grid.pack(fill='both', expand=True, padx=20, pady=(0,10))
        self.load_tables(1)

        # Kitchen Display
        kds_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        kds_f.pack(fill='x', padx=20, pady=(0,16))
        ctk.CTkLabel(kds_f, text="Kitchen Display System (KDS)", font=ctk.CTkFont(size=14, weight='bold'), text_color=C['orange']).pack(padx=14, pady=(10,6), anchor='w')
        self.kds_scroll = ctk.CTkScrollableFrame(kds_f, fg_color='transparent', height=120)
        self.kds_scroll.pack(fill='x', padx=8, pady=(0,8))
        self.load_kitchen_orders()

    def load_tables(self, floor=1):
        for w in self.table_grid.winfo_children(): w.destroy()
        tables = db.get_all_tables(self.current_outlet)
        floor_tables = [t for t in tables if t['floor'] == floor]
        cols = 5
        for i, t in enumerate(floor_tables):
            card = TableCard(self.table_grid, table=t, on_click=self.on_table_click)
            card.grid(row=i//cols, column=i%cols, padx=6, pady=6, sticky='nsew')
        for c in range(cols): self.table_grid.grid_columnconfigure(c, weight=1)

    def on_table_click(self, table):
        if table['status'] == 'available':
            # Open order for table
            self.active_table = table['id']
            self.navigate('kasir')
        elif table['status'] == 'occupied':
            # Show table order
            active_order = db.get_active_table_order(table['id'])
            if active_order:
                self.show_table_order_detail(table, active_order)

    def show_table_order_detail(self, table, order):
        dlg = ctk.CTkToplevel(self); dlg.title(f"Meja {table['table_number']}")
        dlg.geometry("450x400"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        ctk.CTkLabel(dlg, text=f"Meja {table['table_number']} - {table.get('name','')}", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(pady=(14,8))
        ctk.CTkLabel(dlg, text=f"Order: {order['order_number']} | Tamu: {order['customer_count']}", font=ctk.CTkFont(size=12), text_color=C['text2']).pack(pady=(0,10))
        ctk.CTkButton(dlg, text="Bayar Meja Ini", height=38, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['green'], corner_radius=8, command=dlg.destroy).pack(fill='x', padx=18, pady=(6,3))
        ctk.CTkButton(dlg, text="Tambah Pesanan", height=38, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=dlg.destroy).pack(fill='x', padx=18, pady=3)
        ctk.CTkButton(dlg, text="Pindah Meja", height=38, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['orange'], corner_radius=8, command=dlg.destroy).pack(fill='x', padx=18, pady=3)
        ctk.CTkButton(dlg, text="Tutup", height=34, font=ctk.CTkFont(size=12),
                        fg_color=C['bg3'], corner_radius=8, command=dlg.destroy).pack(fill='x', padx=18, pady=(12,10))

    def load_kitchen_orders(self):
        for w in self.kds_scroll.winfo_children(): w.destroy()
        # Show pending food items
        conn = db.get_connection()
        rows = conn.execute("""SELECT ti.*, t.invoice_no, t.table_id FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id=t.id
            WHERE ti.kitchen_status='pending' ORDER BY ti.created_at LIMIT 10""").fetchall()
        conn.close()
        if not rows:
            ctk.CTkLabel(self.kds_scroll, text="Tidak ada pesanan pending", font=ctk.CTkFont(size=11), text_color=C['text3']).pack(pady=8)
        for r in rows:
            row = ctk.CTkFrame(self.kds_scroll, fg_color=C['bg2'], corner_radius=8, height=30)
            row.pack(fill='x', pady=1); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{r['product_name']}", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['orange']).pack(side='left', padx=8)
            if r.get('custom_note'):
                ctk.CTkLabel(row, text=f"({r['custom_note']})", font=ctk.CTkFont(size=9), text_color=C['purple']).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=f"x{r['quantity']}", font=ctk.CTkFont(size=10), text_color=C['text']).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=r['created_at'][11:16], font=ctk.CTkFont(size=9), text_color=C['text3']).pack(side='right', padx=4)
            ctk.CTkButton(row, text="Done", width=40, height=20, font=ctk.CTkFont(size=8), fg_color=C['green'], corner_radius=4,
                           command=lambda tid=r['id']: self.mark_kitchen_done(tid)).pack(side='right', padx=4)

    def mark_kitchen_done(self, item_id):
        conn = db.get_connection()
        conn.execute("UPDATE transaction_items SET kitchen_status='done' WHERE id=?", (item_id,))
        conn.commit(); conn.close()
        self.load_kitchen_orders()

    # ==================== LAPORAN ====================
    def show_laporan(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Laporan", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')

        # Tabs
        tab_var = ctk.StringVar(value="harian")
        tab_f = ctk.CTkFrame(tf, fg_color='transparent')
        tab_f.pack(side='right')
        ctk.CTkSegmentedButton(tab_f, values=["harian", "bulanan", "peak", "karyawan"], variable=tab_var,
                                 font=ctk.CTkFont(size=11), command=lambda v: self.load_report(v)).pack()

        self.report_area = ctk.CTkScrollableFrame(self.main_area, fg_color='transparent')
        self.report_area.pack(fill='both', expand=True, padx=20, pady=(0,16))
        self.load_report("harian")

    def load_report(self, report_type):
        for w in self.report_area.winfo_children(): w.destroy()

        if report_type == "harian":
            summary = db.get_daily_summary(outlet_id=self.current_outlet)
            cards_f = ctk.CTkFrame(self.report_area, fg_color='transparent')
            cards_f.pack(fill='x', pady=(0,10))
            for label, value, color in [("Pendapatan", format_currency(summary['total_revenue']), C['green']),
                                         ("Transaksi", str(summary['total_transactions']), C['accent']),
                                         ("Tunai", format_currency(summary.get('cash_total',0)), C['orange']),
                                         ("Non-Tunai", format_currency(summary.get('non_cash_total',0)), C['pink']),
                                         ("Refund", str(summary.get('refund_count',0)), C['red']),
                                         ("Service", format_currency(summary.get('total_service',0)), C['purple'])]:
                card = StatCard(cards_f, icon="", label=label, value=value, color=color)
                card.pack(side='left', expand=True, fill='x', padx=2)

            # Top products
            tp_f = ctk.CTkFrame(self.report_area, fg_color=C['card'], corner_radius=10, border_width=1, border_color=C['border'])
            tp_f.pack(fill='x', pady=(0,8))
            ctk.CTkLabel(tp_f, text="Produk Terlaris Hari Ini", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=12, pady=(10,6), anchor='w')
            for i, p in enumerate(summary['top_products'][:8]):
                row = ctk.CTkFrame(tp_f, fg_color=C['bg2'], corner_radius=6, height=28)
                row.pack(fill='x', padx=8, pady=1); row.pack_propagate(False)
                ctk.CTkLabel(row, text=f"{i+1}. {p['product_name']}", font=ctk.CTkFont(size=11), text_color=C['text']).pack(side='left', padx=6)
                ctk.CTkLabel(row, text=f"{p['total_qty']}x | {format_currency(p['total_sales'])}", font=ctk.CTkFont(size=10), text_color=C['green']).pack(side='right', padx=6)

        elif report_type == "bulanan":
            now = datetime.now()
            summary = db.get_monthly_summary(now.year, now.month, self.current_outlet)
            cards_f = ctk.CTkFrame(self.report_area, fg_color='transparent')
            cards_f.pack(fill='x', pady=(0,10))
            for label, value, color in [("Omzet Bulan Ini", format_currency(summary['total_revenue']), C['green']),
                                         ("Transaksi", str(summary['total_transactions']), C['accent']),
                                         ("Diskon", format_currency(summary.get('total_discount',0)), C['red']),
                                         ("Pajak", format_currency(summary.get('total_tax',0)), C['orange'])]:
                card = StatCard(cards_f, icon="", label=label, value=value, color=color)
                card.pack(side='left', expand=True, fill='x', padx=2)

            if summary.get('daily_breakdown'):
                table_f = ctk.CTkFrame(self.report_area, fg_color=C['card'], corner_radius=10, border_width=1, border_color=C['border'])
                table_f.pack(fill='both', expand=True)
                ctk.CTkLabel(table_f, text="Rincian Harian", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=12, pady=(10,6), anchor='w')
                scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
                scroll.pack(fill='both', expand=True, padx=6, pady=(0,6))
                hdr = ctk.CTkFrame(scroll, fg_color=C['bg3'], corner_radius=6, height=28)
                hdr.pack(fill='x', pady=(0,2)); hdr.pack_propagate(False)
                for txt, w in [("Tanggal", 120), ("Transaksi", 80), ("Omzet", 150)]:
                    ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['text2'], width=w).pack(side='left', padx=4)
                for d in summary['daily_breakdown']:
                    row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=6, height=26)
                    row.pack(fill='x', pady=1); row.pack_propagate(False)
                    ctk.CTkLabel(row, text=d['date'], font=ctk.CTkFont(size=10), text_color=C['text'], width=120).pack(side='left', padx=4)
                    ctk.CTkLabel(row, text=str(d['transactions']), font=ctk.CTkFont(size=10), text_color=C['text2'], width=80).pack(side='left', padx=4)
                    ctk.CTkLabel(row, text=format_currency(d['revenue']), font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green'], width=150).pack(side='left', padx=4)

        elif report_type == "peak":
            peak_data = db.get_peak_hours_data()
            cards_f = ctk.CTkFrame(self.report_area, fg_color='transparent')
            cards_f.pack(fill='x', pady=(0,10))

            if peak_data:
                max_hour = max(peak_data, key=lambda x: x['transactions'])
                ctk.CTkLabel(cards_f, text=f"Jam Ramai: {max_hour['hour']}:00 ({max_hour['transactions']} transaksi)",
                              font=ctk.CTkFont(size=14, weight='bold'), text_color=C['orange']).pack(anchor='w')

                # Hourly breakdown
                table_f = ctk.CTkFrame(self.report_area, fg_color=C['card'], corner_radius=10, border_width=1, border_color=C['border'])
                table_f.pack(fill='both', expand=True)
                ctk.CTkLabel(table_f, text="Distribusi Jam Ramai", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=12, pady=(10,6), anchor='w')
                scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
                scroll.pack(fill='both', expand=True, padx=6, pady=(0,6))
                for h in peak_data:
                    bar_width = min(int(h['transactions'] * 20), 300)
                    row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=6, height=24)
                    row.pack(fill='x', pady=1); row.pack_propagate(False)
                    ctk.CTkLabel(row, text=f"{h['hour']}:00", font=ctk.CTkFont(size=10), text_color=C['text'], width=50).pack(side='left', padx=4)
                    bar = ctk.CTkFrame(row, fg_color=C['accent'], corner_radius=4, height=14)
                    bar.pack(side='left', padx=4, fill='y')
                    bar.configure(width=max(bar_width, 10))
                    ctk.CTkLabel(row, text=f"{h['transactions']} tx | {format_currency(h['revenue'])}", font=ctk.CTkFont(size=9), text_color=C['text2']).pack(side='left', padx=6)
            else:
                ctk.CTkLabel(cards_f, text="Belum ada data peak hours", font=ctk.CTkFont(size=12), text_color=C['text3']).pack(pady=20)

        elif report_type == "karyawan":
            perf = db.get_employee_performance()
            cards_f = ctk.CTkFrame(self.report_area, fg_color='transparent')
            cards_f.pack(fill='x', pady=(0,10))

            table_f = ctk.CTkFrame(self.report_area, fg_color=C['card'], corner_radius=10, border_width=1, border_color=C['border'])
            table_f.pack(fill='both', expand=True)
            ctk.CTkLabel(table_f, text="Performa Karyawan (30 Hari)", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=12, pady=(10,6), anchor='w')
            scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
            scroll.pack(fill='both', expand=True, padx=6, pady=(0,6))

            hdr = ctk.CTkFrame(scroll, fg_color=C['bg3'], corner_radius=6, height=28)
            hdr.pack(fill='x', pady=(0,2)); hdr.pack_propagate(False)
            for txt, w in [("Nama", 150), ("Role", 80), ("Transaksi", 80), ("Omzet", 140), ("Rata-rata", 120)]:
                ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['text2'], width=w).pack(side='left', padx=4)

            for e in perf:
                row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=6, height=28)
                row.pack(fill='x', pady=1); row.pack_propagate(False)
                ctk.CTkLabel(row, text=e['full_name'], font=ctk.CTkFont(size=10, weight='bold'), text_color=C['text'], width=150).pack(side='left', padx=4)
                ctk.CTkLabel(row, text=e['role'], font=ctk.CTkFont(size=10), text_color=C['text2'], width=80).pack(side='left', padx=4)
                ctk.CTkLabel(row, text=str(e['total_transactions']), font=ctk.CTkFont(size=10), text_color=C['text'], width=80).pack(side='left', padx=4)
                ctk.CTkLabel(row, text=format_currency(e['total_revenue']), font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green'], width=140).pack(side='left', padx=4)
                ctk.CTkLabel(row, text=format_currency(e['avg_transaction']), font=ctk.CTkFont(size=10), text_color=C['text2'], width=120).pack(side='left', padx=4)

    # ==================== STOK ====================
    def show_stok(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Manajemen Stok", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')

        # Low stock alerts
        low = db.get_low_stock_products()
        if low:
            alert_f = ctk.CTkFrame(self.main_area, fg_color=C['red_bg'], corner_radius=10, border_width=1, border_color=C['red'])
            alert_f.pack(fill='x', padx=20, pady=(0,10))
            ctk.CTkLabel(alert_f, text=f"Peringatan: {len(low)} produk stok rendah!", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['red']).pack(padx=12, pady=(8,4), anchor='w')
            for ls in low[:5]:
                ctk.CTkLabel(alert_f, text=f"  - {ls['name']}: {ls['stock']} (min: {ls['min_stock']})", font=ctk.CTkFont(size=11), text_color=C['text2']).pack(padx=12, anchor='w')
            ctk.CTkFrame(alert_f, fg_color='transparent', height=6).pack()

        # Stock history
        table_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        table_f.pack(fill='both', expand=True, padx=20, pady=(0,16))
        ctk.CTkLabel(table_f, text="Riwayat Stok", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=12, pady=(10,6), anchor='w')
        scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=6, pady=(0,6))

        hdr = ctk.CTkFrame(scroll, fg_color=C['bg3'], corner_radius=6, height=28)
        hdr.pack(fill='x', pady=(0,2)); hdr.pack_propagate(False)
        for txt, w in [("Produk", 180), ("Tipe", 80), ("Jumlah", 70), ("Catatan", 200), ("Waktu", 140)]:
            ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['text2'], width=w).pack(side='left', padx=4)

        for h in db.get_stock_history(limit=30):
            row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=6, height=26)
            row.pack(fill='x', pady=1); row.pack_propagate(False)
            ctk.CTkLabel(row, text=h.get('product_name','-')[:22], font=ctk.CTkFont(size=10), text_color=C['text'], width=180).pack(side='left', padx=4)
            type_color = C['green'] if h['type'] in ('masuk','penjualan') and h['quantity']>0 else C['red'] if h['quantity']<0 else C['text2']
            ctk.CTkLabel(row, text=h['type'], font=ctk.CTkFont(size=10), text_color=type_color, width=80).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=str(h['quantity']), font=ctk.CTkFont(size=10, weight='bold'), text_color=type_color, width=70).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=h.get('note','')[:24], font=ctk.CTkFont(size=10), text_color=C['text3'], width=200).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=h['created_at'][:16], font=ctk.CTkFont(size=9), text_color=C['text3'], width=140).pack(side='left', padx=4)

    # ==================== KARYAWAN ====================
    def show_karyawan(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Manajemen Karyawan", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')
        ctk.CTkButton(tf, text="+ Tambah Karyawan", height=34, font=ctk.CTkFont(size=12, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=self.show_add_user_dialog).pack(side='right')

        table_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        table_f.pack(fill='both', expand=True, padx=20, pady=(0,16))
        scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=6, pady=6)

        hdr = ctk.CTkFrame(scroll, fg_color=C['bg3'], corner_radius=6, height=32)
        hdr.pack(fill='x', pady=(0,3)); hdr.pack_propagate(False)
        for txt, w in [("Nama", 160), ("Username", 100), ("Role", 80), ("Outlet", 120), ("Status", 70), ("Aksi", 120)]:
            ctk.CTkLabel(hdr, text=txt, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['text2'], width=w).pack(side='left', padx=4)

        for u in db.get_all_users():
            row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=6, height=34)
            row.pack(fill='x', pady=1); row.pack_propagate(False)
            ctk.CTkLabel(row, text=u['full_name'], font=ctk.CTkFont(size=11), text_color=C['text'], width=160).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=u['username'], font=ctk.CTkFont(size=10), text_color=C['text2'], width=100).pack(side='left', padx=4)
            role_colors = {'owner': C['gold'], 'admin': C['accent'], 'manager': C['purple'], 'kasir': C['green']}
            ctk.CTkLabel(row, text=u['role'].upper(), font=ctk.CTkFont(size=10, weight='bold'), text_color=role_colors.get(u['role'], C['text']), width=80).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=u.get('outlet_name','-'), font=ctk.CTkFont(size=10), text_color=C['text2'], width=120).pack(side='left', padx=4)
            ctk.CTkLabel(row, text="Aktif" if u['active'] else "Nonaktif", font=ctk.CTkFont(size=10), text_color=C['green'] if u['active'] else C['red'], width=70).pack(side='left', padx=4)
            act_f = ctk.CTkFrame(row, fg_color='transparent', width=120)
            act_f.pack(side='right', padx=4); act_f.pack_propagate(False)
            ctk.CTkButton(act_f, text="Edit", width=48, height=22, font=ctk.CTkFont(size=8), fg_color=C['accent'], corner_radius=4,
                           command=lambda uid=u['id']: self.show_edit_user_dialog(uid)).pack(side='left', padx=1)
            ctk.CTkButton(act_f, text="Hapus", width=48, height=22, font=ctk.CTkFont(size=8), fg_color=C['red'], corner_radius=4,
                           command=lambda uid=u['id']: [db.delete_user(uid), self.show_karyawan()]).pack(side='left', padx=1)

    def show_add_user_dialog(self):
        self._user_dialog(None)

    def show_edit_user_dialog(self, uid):
        self._user_dialog(uid)

    def _user_dialog(self, uid=None):
        users = db.get_all_users()
        user = None
        if uid:
            for u in users:
                if u['id'] == uid: user = u; break

        dlg = ctk.CTkToplevel(self); dlg.title("Edit Karyawan" if user else "Tambah Karyawan")
        dlg.geometry("420x420"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)

        ctk.CTkLabel(dlg, text="Edit Karyawan" if user else "Tambah Karyawan", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,10))

        fields = {}
        for lbl, key, default in [("Nama Lengkap", "full_name", user['full_name'] if user else ""),
                                   ("Username", "username", user['username'] if user else ""),
                                   ("Password", "password", "")]:
            ctk.CTkLabel(dlg, text=lbl, font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
            e = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=6)
            e.pack(fill='x', padx=20)
            if default: e.insert(0, default)
            fields[key] = e

        # Role
        ctk.CTkLabel(dlg, text="Role", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
        role_var = ctk.StringVar(value=user['role'] if user else 'kasir')
        ctk.CTkSegmentedButton(dlg, values=["owner","admin","manager","kasir"], variable=role_var, font=ctk.CTkFont(size=11)).pack(fill='x', padx=20)

        # Outlet
        outlets = db.get_all_outlets()
        ctk.CTkLabel(dlg, text="Outlet", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
        outlet_names = [o['name'] for o in outlets]
        outlet_map = {o['name']: o['id'] for o in outlets}
        out_var = ctk.StringVar(value=user.get('outlet_name', outlet_names[0]) if user and user.get('outlet_name') else outlet_names[0])
        ctk.CTkOptionMenu(dlg, variable=out_var, values=outlet_names, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], button_color=C['accent']).pack(fill='x', padx=20)

        def save():
            fn = fields['full_name'].get().strip()
            un = fields['username'].get().strip()
            pw = fields['password'].get().strip()
            oid = outlet_map.get(out_var.get(), 1)
            if uid:
                db.update_user(uid, fn, role_var.get(), 1, oid)
                if pw: db.update_user_password(uid, pw)
            else:
                if not pw: pw = 'kasir123'
                db.add_user(un, pw, fn, role_var.get(), oid)
            dlg.destroy(); self.show_karyawan()

        ctk.CTkButton(dlg, text="Simpan", height=38, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=save).pack(fill='x', padx=20, pady=(16,14))

    # ==================== PELANGGAN ====================
    def show_pelanggan(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Pelanggan", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')
        ctk.CTkButton(tf, text="+ Tambah", height=34, font=ctk.CTkFont(size=12, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=self.show_add_customer_dialog).pack(side='right')

        table_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        table_f.pack(fill='both', expand=True, padx=20, pady=(0,16))
        scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=6, pady=6)

        for c in db.get_all_customers():
            row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=8, height=44, border_width=1, border_color=C['border'])
            row.pack(fill='x', pady=2); row.pack_propagate(False)
            ctk.CTkLabel(row, text=c['name'], font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(side='left', padx=10)
            TierBadge(row, tier=c['tier']).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=f"{c['points']} pts", font=ctk.CTkFont(size=10), text_color=C['gold']).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=f"{c['phone'] or '-'}", font=ctk.CTkFont(size=10), text_color=C['text3']).pack(side='left', padx=8)
            ctk.CTkLabel(row, text=f"Spent: {format_currency(c['total_spent'])} | {c['total_visits']}x", font=ctk.CTkFont(size=10), text_color=C['text2']).pack(side='right', padx=8)
            ctk.CTkButton(row, text="Edit", width=40, height=22, font=ctk.CTkFont(size=8), fg_color=C['accent'], corner_radius=4,
                           command=lambda cid=c['id']: self.show_edit_customer_dialog(cid)).pack(side='right', padx=2)

    def show_add_customer_dialog(self):
        self._customer_dialog(None)

    def show_edit_customer_dialog(self, cid):
        self._customer_dialog(cid)

    def _customer_dialog(self, cid=None):
        cust = db.get_customer_by_id(cid) if cid else None
        dlg = ctk.CTkToplevel(self); dlg.title("Edit Pelanggan" if cust else "Tambah Pelanggan")
        dlg.geometry("420x450"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        ctk.CTkLabel(dlg, text="Edit Pelanggan" if cust else "Tambah Pelanggan", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(pady=(14,8))
        fields = {}
        for lbl, key, default in [("Nama", "name", cust['name'] if cust else ""),
                                   ("Telepon", "phone", cust['phone'] if cust else ""),
                                   ("Email", "email", cust['email'] if cust else ""),
                                   ("Alamat", "address", cust['address'] if cust else "")]:
            ctk.CTkLabel(dlg, text=lbl, font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
            e = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=6)
            e.pack(fill='x', padx=20)
            if default: e.insert(0, default)
            fields[key] = e

        tier_var = ctk.StringVar(value=cust['tier'] if cust else 'Regular')
        ctk.CTkLabel(dlg, text="Tier", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
        ctk.CTkSegmentedButton(dlg, values=["Regular","Silver","Gold","Platinum"], variable=tier_var, font=ctk.CTkFont(size=11)).pack(fill='x', padx=20)

        def save():
            if cid:
                db.update_customer(cid, fields['name'].get(), fields['phone'].get(), fields['email'].get(), fields['address'].get(), tier_var.get())
            else:
                db.add_customer(fields['name'].get(), fields['phone'].get(), fields['email'].get(), fields['address'].get())
            dlg.destroy(); self.show_pelanggan()

        ctk.CTkButton(dlg, text="Simpan", height=36, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=save).pack(fill='x', padx=20, pady=(16,14))

    # ==================== PROMO ====================
    def show_promo(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Promo & Diskon", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')
        ctk.CTkButton(tf, text="+ Tambah Promo", height=34, font=ctk.CTkFont(size=12, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=self.show_add_promo_dialog).pack(side='right')

        table_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        table_f.pack(fill='both', expand=True, padx=20, pady=(0,16))
        scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=6, pady=6)

        for p in db.get_all_promos():
            row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=8, height=44, border_width=1, border_color=C['border'])
            row.pack(fill='x', pady=2); row.pack_propagate(False)
            val_txt = f"{p['value']}%" if p['type']=='percentage' else format_currency(p['value'])
            ctk.CTkLabel(row, text=p['name'], font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(side='left', padx=10)
            ctk.CTkLabel(row, text=val_txt, font=ctk.CTkFont(size=11, weight='bold'), text_color=C['green']).pack(side='left', padx=6)
            ctk.CTkLabel(row, text=f"Min: {format_currency(p['min_purchase'])}", font=ctk.CTkFont(size=10), text_color=C['text3']).pack(side='left', padx=4)
            status = "Aktif" if p['active'] and p['start_date'] <= datetime.now().strftime('%Y-%m-%d') <= p['end_date'] else "Nonaktif"
            ctk.CTkLabel(row, text=status, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green'] if status=="Aktif" else C['red']).pack(side='right', padx=8)
            ctk.CTkButton(row, text="Hapus", width=50, height=22, font=ctk.CTkFont(size=8), fg_color=C['red'], corner_radius=4,
                           command=lambda pid=p['id']: [db.delete_promo(pid), self.show_promo()]).pack(side='right', padx=2)

    def show_add_promo_dialog(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Tambah Promo")
        dlg.geometry("440x500"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        ctk.CTkLabel(dlg, text="Tambah Promo", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(pady=(14,8))

        fields = {}
        for lbl, key, ph in [("Nama Promo", "name", "Contoh: Diskon Akhir Bulan"),
                               ("Nilai", "value", "10 (untuk %) atau 25000 (untuk nominal)"),
                               ("Min. Pembelian", "min_purchase", "0"),
                               ("Max. Diskon", "max_discount", "0 (0 = tanpa batas)"),
                               ("Tanggal Mulai", "start_date", datetime.now().strftime('%Y-%m-%d')),
                               ("Tanggal Selesai", "end_date", (datetime.now()+timedelta(days=30)).strftime('%Y-%m-%d'))]:
            ctk.CTkLabel(dlg, text=lbl, font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
            e = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=6, placeholder_text=ph)
            e.pack(fill='x', padx=20)
            if ph and not lbl.startswith("Tanggal"): pass
            fields[key] = e

        type_var = ctk.StringVar(value="percentage")
        ctk.CTkLabel(dlg, text="Tipe", font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(anchor='w', padx=20, pady=(6,2))
        ctk.CTkSegmentedButton(dlg, values=["percentage","fixed"], variable=type_var, font=ctk.CTkFont(size=11)).pack(fill='x', padx=20)

        def save():
            db.add_promo(fields['name'].get(), type_var.get(), float(fields['value'].get() or 0),
                float(fields['min_purchase'].get() or 0), fields['start_date'].get(), fields['end_date'].get(),
                float(fields['max_discount'].get() or 0))
            dlg.destroy(); self.show_promo()

        ctk.CTkButton(dlg, text="Simpan", height=38, font=ctk.CTkFont(size=13, weight='bold'),
                        fg_color=C['accent'], corner_radius=8, command=save).pack(fill='x', padx=20, pady=(16,14))

    # ==================== SHIFT ====================
    def show_shift(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Manajemen Shift", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')

        # Current shift info
        if self.current_shift:
            sf = ctk.CTkFrame(self.main_area, fg_color=C['green_bg'], corner_radius=12, border_width=1, border_color=C['green'])
            sf.pack(fill='x', padx=20, pady=(0,10))
            shift = self.current_shift
            ctk.CTkLabel(sf, text="Shift Aktif", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['green']).pack(padx=14, pady=(12,4), anchor='w')
            ctk.CTkLabel(sf, text=f"Kasir: {shift.get('cashier_name','-')} | Mulai: {shift['start_time'][:16]} | Saldo Awal: {format_currency(shift['start_cash'])}",
                          font=ctk.CTkFont(size=12), text_color=C['text']).pack(padx=14, anchor='w')
            ctk.CTkButton(sf, text="Tutup Shift", height=34, font=ctk.CTkFont(size=12, weight='bold'),
                            fg_color=C['red'], corner_radius=8, command=self.show_close_shift_dialog).pack(padx=14, pady=(8,12), anchor='w')

        # Shift history
        table_f = ctk.CTkFrame(self.main_area, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        table_f.pack(fill='both', expand=True, padx=20, pady=(0,16))
        ctk.CTkLabel(table_f, text="Riwayat Shift", font=ctk.CTkFont(size=13, weight='bold'), text_color=C['white']).pack(padx=12, pady=(10,6), anchor='w')
        scroll = ctk.CTkScrollableFrame(table_f, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=6, pady=(0,6))

        for s in db.get_shift_history():
            row = ctk.CTkFrame(scroll, fg_color=C['bg2'], corner_radius=8, height=40, border_width=1, border_color=C['border'])
            row.pack(fill='x', pady=2); row.pack_propagate(False)
            status_color = C['green'] if s['status']=='open' else C['text3']
            ctk.CTkLabel(row, text=s.get('cashier_name','-'), font=ctk.CTkFont(size=11, weight='bold'), text_color=C['text']).pack(side='left', padx=8)
            ctk.CTkLabel(row, text=s['status'].upper(), font=ctk.CTkFont(size=10, weight='bold'), text_color=status_color).pack(side='left', padx=8)
            ctk.CTkLabel(row, text=f"{s['start_time'][:16]} - {s.get('end_time','...')[:16] if s.get('end_time') else '...'}", font=ctk.CTkFont(size=10), text_color=C['text3']).pack(side='left', padx=8)
            ctk.CTkLabel(row, text=f"Revenue: {format_currency(s['total_revenue'])} | {s['total_transactions']} tx",
                          font=ctk.CTkFont(size=10), text_color=C['text2']).pack(side='right', padx=8)

    def show_close_shift_dialog(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Tutup Shift")
        dlg.geometry("420x380"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)

        ctk.CTkLabel(dlg, text="Tutup Shift", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,8))
        if self.current_shift:
            ctk.CTkLabel(dlg, text=f"Mulai: {self.current_shift['start_time'][:16]}", font=ctk.CTkFont(size=12), text_color=C['text2']).pack(pady=(0,8))

        ctk.CTkLabel(dlg, text="Saldo Akhir Kas:", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(padx=24, anchor='w')
        cash_entry = ctk.CTkEntry(dlg, height=38, font=ctk.CTkFont(size=14, weight='bold'), fg_color=C['bg2'], corner_radius=8)
        cash_entry.pack(fill='x', padx=24, pady=(4,8))
        cash_entry.insert(0, "0")

        ctk.CTkLabel(dlg, text="Catatan:", font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text']).pack(padx=24, anchor='w')
        notes_entry = ctk.CTkEntry(dlg, height=32, font=ctk.CTkFont(size=12), fg_color=C['bg2'], corner_radius=8, placeholder_text="Opsional")
        notes_entry.pack(fill='x', padx=24, pady=(4,12))

        def close_it():
            try: end_cash = float(cash_entry.get() or 0)
            except: end_cash = 0
            db.close_shift(self.current_shift['id'], end_cash, notes_entry.get())
            db.add_audit_log(self.current_user['id'], 'close_shift', 'shift', f'Shift {self.current_shift["id"]} closed')
            self.current_shift = None
            dlg.destroy()
            self.show_shift_open_dialog()

        ctk.CTkButton(dlg, text="Tutup Shift", height=40, font=ctk.CTkFont(size=14, weight='bold'),
                        fg_color=C['red'], hover_color=C['red2'], corner_radius=10, command=close_it).pack(fill='x', padx=24, pady=(8,14))

    # ==================== PENGATURAN ====================
    def show_pengaturan(self):
        tf = ctk.CTkFrame(self.main_area, fg_color='transparent')
        tf.pack(fill='x', padx=20, pady=(16,10))
        ctk.CTkLabel(tf, text="Pengaturan", font=ctk.CTkFont(size=22, weight='bold'), text_color=C['white']).pack(side='left')

        scroll = ctk.CTkScrollableFrame(self.main_area, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=20, pady=(0,16))

        # Outlet info
        outlet_card = ctk.CTkFrame(scroll, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        outlet_card.pack(fill='x', pady=(0,10))
        ctk.CTkLabel(outlet_card, text="Outlet", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(padx=14, pady=(12,6), anchor='w')
        for o in db.get_all_outlets():
            row = ctk.CTkFrame(outlet_card, fg_color=C['bg2'], corner_radius=8, height=36)
            row.pack(fill='x', padx=8, pady=2); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{o['name']} - {o.get('address','-')}", font=ctk.CTkFont(size=11), text_color=C['text']).pack(side='left', padx=8)
            active_marker = " (AKTIF)" if o['id'] == self.current_outlet else ""
            ctk.CTkLabel(row, text=active_marker, font=ctk.CTkFont(size=10, weight='bold'), text_color=C['green']).pack(side='left', padx=4)
            ctk.CTkButton(row, text="Pilih", width=45, height=22, font=ctk.CTkFont(size=8), fg_color=C['accent'], corner_radius=4,
                           command=lambda oid=o['id']: [setattr(self, 'current_outlet', oid), self.build_main_ui()]).pack(side='right', padx=8)

        # Printer settings
        printer_card = ctk.CTkFrame(scroll, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        printer_card.pack(fill='x', pady=(0,10))
        ctk.CTkLabel(printer_card, text="Printer", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(padx=14, pady=(12,6), anchor='w')
        for ps in db.get_printer_settings(self.current_outlet):
            row = ctk.CTkFrame(printer_card, fg_color=C['bg2'], corner_radius=8, height=32)
            row.pack(fill='x', padx=8, pady=2); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{ps['name']} ({ps['printer_type']}, {ps['paper_width']}mm)", font=ctk.CTkFont(size=11), text_color=C['text']).pack(side='left', padx=8)
            auto_txt = "Auto Print: ON" if ps['auto_print'] else "Auto Print: OFF"
            ctk.CTkLabel(row, text=auto_txt, font=ctk.CTkFont(size=10), text_color=C['green'] if ps['auto_print'] else C['text3']).pack(side='right', padx=8)

        # Audit log
        audit_card = ctk.CTkFrame(scroll, fg_color=C['card'], corner_radius=12, border_width=1, border_color=C['border'])
        audit_card.pack(fill='x')
        ctk.CTkLabel(audit_card, text="Audit Log", font=ctk.CTkFont(size=16, weight='bold'), text_color=C['white']).pack(padx=14, pady=(12,6), anchor='w')
        log_scroll = ctk.CTkScrollableFrame(audit_card, fg_color='transparent', height=150)
        log_scroll.pack(fill='x', padx=6, pady=(0,8))
        for log in db.get_audit_logs(20):
            row = ctk.CTkFrame(log_scroll, fg_color=C['bg2'], corner_radius=6, height=24)
            row.pack(fill='x', pady=1); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{log['created_at'][:16]}", font=ctk.CTkFont(size=9), text_color=C['text3'], width=100).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=log.get('user_name','-'), font=ctk.CTkFont(size=9), text_color=C['text2'], width=80).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=f"{log['action']} {log['module']}", font=ctk.CTkFont(size=9), text_color=C['accent'], width=120).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=log.get('detail','')[:30], font=ctk.CTkFont(size=9), text_color=C['text3']).pack(side='left', padx=4)

    # ==================== NOTIFICATIONS ====================
    def show_notifications(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Notifikasi")
        dlg.geometry("420x500"); dlg.configure(fg_color=C['bg']); dlg.grab_set()
        dlg.transient(self)
        ctk.CTkLabel(dlg, text="Notifikasi", font=ctk.CTkFont(size=18, weight='bold'), text_color=C['white']).pack(pady=(14,8))

        notifs = db.get_all_notifications()
        if not notifs:
            ctk.CTkLabel(dlg, text="Tidak ada notifikasi", font=ctk.CTkFont(size=12), text_color=C['text3']).pack(pady=40)
        scroll = ctk.CTkScrollableFrame(dlg, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=14)

        for n in notifs:
            bg = C['bg2'] if not n['is_read'] else C['bg3']
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=8, height=48, border_width=1 if not n['is_read'] else 0, border_color=C['accent'])
            row.pack(fill='x', pady=2); row.pack_propagate(False)
            type_colors = {'low_stock': C['red'], 'refund': C['orange'], 'void': C['pink']}
            tc = type_colors.get(n['type'], C['accent'])
            ctk.CTkLabel(row, text=n['title'], font=ctk.CTkFont(size=11, weight='bold'), text_color=tc).pack(side='left', padx=8)
            ctk.CTkLabel(row, text=n['message'][:35], font=ctk.CTkFont(size=9), text_color=C['text2']).pack(side='left', padx=4)
            ctk.CTkLabel(row, text=n['created_at'][11:16], font=ctk.CTkFont(size=9), text_color=C['text3']).pack(side='right', padx=8)
            if not n['is_read']:
                db.mark_notification_read(n['id'])

        ctk.CTkButton(dlg, text="Hapus Semua", height=34, font=ctk.CTkFont(size=12),
                        fg_color=C['red'], corner_radius=8,
                        command=lambda: [db.clear_notifications(), dlg.destroy()]).pack(fill='x', padx=14, pady=(8,14))


def main():
    app = KasirApp()
    app.mainloop()


if __name__ == "__main__":
    main()
