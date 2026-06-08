#!/usr/bin/env python3
"""
KASIR PRO V3 - Full Moka-style POS System Launcher
Features: Split Bill, Merge Bill, Void, Refund, Table Management, Kitchen Display,
          Product Variations, Multi Outlet, Peak Hours, Employee Performance, Offline Mode
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
db.init_database()

from main import main

if __name__ == "__main__":
    main()
