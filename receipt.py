"""
Receipt Module V3 - Full Moka-style POS Receipt
Features: Outlet info, variations, custom notes, void/refund status, split bill, service charge, kitchen info
"""

import os
from datetime import datetime

RECEIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipts")
STORE_NAME = "KASIR PRO V3"
STORE_ADDRESS = "Jl. Merdeka No. 123, Jakarta"
STORE_PHONE = "021-12345678"
STORE_TAGLINE = "Sistem Manajemen Bisnis Lengkap"


def ensure_receipt_dir():
    os.makedirs(RECEIPT_DIR, exist_ok=True)


def format_currency(amount: float) -> str:
    return f"Rp{amount:,.0f}".replace(",", ".")


def generate_receipt_text(transaction: dict, outlet_info: dict = None) -> str:
    lines = []
    w = 44

    # Header
    lines.append("=" * w)
    store_name = outlet_info.get('name', STORE_NAME) if outlet_info else STORE_NAME
    store_addr = outlet_info.get('address', STORE_ADDRESS) if outlet_info else STORE_ADDRESS
    store_phone = outlet_info.get('phone', STORE_PHONE) if outlet_info else STORE_PHONE

    lines.append(store_name.center(w))
    if store_addr: lines.append(store_addr.center(w))
    if store_phone: lines.append(f"Telp: {store_phone}".center(w))
    lines.append(STORE_TAGLINE.center(w))
    lines.append("=" * w)
    lines.append("")

    # Status badge
    status = transaction.get('status', 'completed')
    is_voided = transaction.get('is_voided', 0)

    if is_voided:
        lines.append("*** VOID / DIBATALKAN ***".center(w))
        if transaction.get('void_reason'):
            lines.append(f"Alasan: {transaction['void_reason']}".center(w))
        lines.append("")
    elif status == 'refunded':
        lines.append("*** REFUNDED / DIKEMBALIKAN ***".center(w))
        if transaction.get('refund_reason'):
            lines.append(f"Alasan: {transaction['refund_reason']}".center(w))
        lines.append("")

    # Transaction info
    lines.append(f"No       : {transaction['invoice_no']}")
    lines.append(f"Tanggal  : {transaction['created_at']}")
    lines.append(f"Kasir    : {transaction.get('cashier_name', '-')}")
    lines.append(f"Pelanggan: {transaction.get('customer_name', 'Umum')}")
    lines.append(f"Metode   : {transaction.get('payment_method', 'Tunai')}")
    if transaction.get('outlet_name'):
        lines.append(f"Outlet   : {transaction['outlet_name']}")
    if transaction.get('custom_notes'):
        lines.append(f"Catatan  : {transaction['custom_notes']}")
    lines.append("-" * w)

    # Items
    for item in transaction.get('items', []):
        name = item['product_name']
        price = item['product_price']
        qty = item['quantity']
        sub = item['subtotal']

        # Variation text
        var_text = item.get('variation_text', '')
        if var_text:
            name += f" ({var_text})"

        # Custom note
        custom_note = item.get('custom_note', '')
        if custom_note:
            name += f" [{custom_note}]"

        price_str = format_currency(price)
        sub_str = format_currency(sub)

        if len(name) > w:
            lines.append(name[:w])
            name = "  " + name[w:]

        lines.append(name)
        detail = f"  {price_str} x {qty}"
        detail = detail.ljust(w - len(sub_str)) + sub_str
        lines.append(detail)

    lines.append("-" * w)

    # Totals
    subtotal = format_currency(transaction['subtotal'])
    discount = format_currency(transaction['discount'])
    tax = format_currency(transaction.get('tax', 0))
    service = format_currency(transaction.get('service_charge', 0))
    total = format_currency(transaction['total'])
    paid = format_currency(transaction['paid'])
    change = format_currency(transaction['change_amount'])

    lines.append(f"Subtotal{'':.>{w - 9 - len(subtotal)}}{subtotal}")

    if transaction.get('discount', 0) > 0:
        disc_type = transaction.get('discount_type', 'manual')
        disc_label = 'Diskon' + (' (Promo)' if disc_type == 'promo' else '')
        lines.append(f"{disc_label}{'':.>{w - len(disc_label) - len(discount)}}{discount}")

    if transaction.get('tax', 0) > 0:
        lines.append(f"Pajak{'':.>{w - 6 - len(tax)}}{tax}")

    if transaction.get('service_charge', 0) > 0:
        lines.append(f"Service{'':.>{w - 8 - len(service)}}{service}")

    lines.append("=" * w)
    lines.append(f"TOTAL{'':.>{w - 6 - len(total)}}{total}")
    lines.append("=" * w)
    lines.append(f"Dibayar{'':.>{w - 8 - len(paid)}}{paid}")
    lines.append(f"Kembalian{'':.>{w - 10 - len(change)}}{change}")

    # Loyalty info
    pts_earned = transaction.get('points_earned', 0)
    pts_used = transaction.get('points_used', 0)
    if pts_earned > 0 or pts_used > 0:
        lines.append("")
        lines.append("--- Loyalty ---")
        if pts_earned > 0:
            lines.append(f"Poin didapat : +{pts_earned}")
        if pts_used > 0:
            lines.append(f"Poin digunakan: -{pts_used}")

    # Split bill info
    if transaction.get('split_from'):
        lines.append("")
        lines.append(f"Split dari: INV-{transaction['split_from']}")

    # Offline indicator
    if transaction.get('is_offline'):
        lines.append("")
        lines.append("* Transaksi Offline *".center(w))

    lines.append("")
    lines.append("~ Terima Kasih ~".center(w))
    lines.append("~ Barang yang sudah dibeli ~".center(w))
    lines.append("~ tidak dapat ditukar/dikembalikan ~".center(w))
    lines.append("=" * w)

    # QR code placeholder
    lines.append("")
    lines.append("[QR Code]".center(w))

    return "\n".join(lines)


def save_receipt(transaction: dict, outlet_info: dict = None) -> str:
    ensure_receipt_dir()
    invoice_no = transaction['invoice_no'].replace('/', '-')
    filename = f"receipt_{invoice_no}.txt"
    filepath = os.path.join(RECEIPT_DIR, filename)
    text = generate_receipt_text(transaction, outlet_info)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    return filepath


def generate_kitchen_ticket(transaction: dict) -> str:
    """Generate kitchen display ticket for food items"""
    lines = []
    w = 36

    lines.append("=" * w)
    lines.append("KITCHEN ORDER".center(w))
    lines.append("=" * w)
    lines.append(f"No: {transaction['invoice_no']}")
    lines.append(f"Meja: {transaction.get('table_id', 'Take Away')}")
    lines.append(f"Waktu: {transaction['created_at'][11:16]}")
    lines.append("-" * w)

    for item in transaction.get('items', []):
        if item.get('is_food') or item.get('kitchen_status') == 'pending':
            lines.append(f"{item['quantity']}x {item['product_name']}")
            if item.get('variation_text'):
                lines.append(f"   Var: {item['variation_text']}")
            if item.get('custom_note'):
                lines.append(f"   NOTE: {item['custom_note']}")

    lines.append("=" * w)
    return "\n".join(lines)


if __name__ == "__main__":
    test = {
        'invoice_no': 'INV-20260608-0001',
        'created_at': '2026-06-08 14:30:00',
        'cashier_name': 'Kasir Satu',
        'customer_name': 'Budi Santoso',
        'payment_method': 'QRIS',
        'discount_type': 'promo',
        'status': 'completed',
        'is_voided': 0,
        'outlet_name': 'Outlet Utama',
        'custom_notes': '',
        'items': [
            {'product_name': 'Nasi Goreng', 'product_price': 22000, 'quantity': 2, 'subtotal': 44000,
             'variation_text': 'Level: Extra Pedas', 'custom_note': 'Tambah telur', 'is_food': 1},
            {'product_name': 'Kopi Susu', 'product_price': 20000, 'quantity': 1, 'subtotal': 20000,
             'variation_text': 'Ukuran: Large', 'custom_note': '', 'is_food': 0},
        ],
        'subtotal': 64000, 'discount': 6400, 'tax': 0, 'service_charge': 3000,
        'total': 60600, 'paid': 100000, 'change_amount': 39400,
        'points_earned': 6, 'points_used': 0
    }
    print(generate_receipt_text(test))
    print("\n\n--- Kitchen Ticket ---\n")
    print(generate_kitchen_ticket(test))
