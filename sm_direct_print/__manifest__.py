# -*- coding: utf-8 -*-
# Copyright 2026 Steven Marp
{
    "name": "Direct Print - Thermal Label & Receipt Printer via QZ Tray",
    "version": "19.0.1.0.0",
    "summary": "Print labels & receipts directly to Zebra, TSC, Epson, thermal printer - ZPL, ESC/POS, no IoT Box",
    "description": """
Direct Print - Thermal Label & Receipt Printer via QZ Tray
============================================================

Print labels and receipts directly to thermal printers without downloading
PDF files. Uses QZ Tray to send raw commands from the browser to USB
or network printers.

Supported Printer Languages
---------------------------
* **ZPL** — Zebra (GK420, ZD220, ZD420, ZT230, ZT410, etc.)
* **EPL** — Eltron / legacy Zebra
* **TSPL** — TSC (TTP-245C, TE200, TE300, etc.)
* **CPCL** — Zebra mobile printers (QL, ZQ series)
* **DPL** — Datamax / Honeywell
* **ESC/POS** — Epson, Star, Bixolon, receipt/POS printers
* **Raw Text** — Any printer accepting plain text

Key Features
------------
* **QZ Tray Integration** — Direct browser-to-printer via WebSocket
* **Printer Management** — Configure multiple printers per company
* **Label Template Designer** — Create reusable label templates with dynamic fields
* **Print from Any Record** — Product, Lot/Serial, Picking, Invoice, or any model
* **Multi-platform** — Windows (USB), Linux (CUPS), Mac (CUPS), Network (TCP)
* **Barcode Support** — Code128, Code39, QR Code, EAN13, UPC, DataMatrix
* **Print Preview** — See label rendering before printing (Labelary API)
* **Print History** — Full audit trail of every print job
* **Batch Printing** — Select multiple records → print all labels at once
* **Copy Control** — Configure number of copies per label
* **OWL Dashboard** — Print stats, recent jobs, printer status

Requirements
------------
* QZ Tray installed on user's PC (free download: https://qz.io/download/)
* Printer connected via USB or network

Keywords: Direct Print | Odoo Direct Print | Zebra Print | Thermal Printer |
ZPL Print | ESC/POS Print | Label Print | Receipt Printer | QZ Tray |
QZ Tray Odoo | Odoo QZ Tray | Print Without Download | Print Directly |
Print Labels from Odoo | Barcode Print | Shipping Label Print | Product Label |
Thermal Label Printing | ZPL Label Designer | Zebra Label Odoo | Odoo Label Printing |
Print from Odoo | Direct Print Pro | Odoo Print Module | Print Directly from Odoo |
Odoo Printing Solution | Local Printer Integration | Network Printer |
USB Printer | Wi-Fi Printer | Bluetooth Printer | Printer Integration |
Print Without Downloading | Print Without PDF | IoTBox Free Print | IoT Box Alternative |
No IoT Box | PrintNode Alternative | Print Automation | Auto Print |
Fast Printing from Odoo | Quick Print | One-Click Print | Seamless Print |
ZPL Printer Support | Zebra Printer Odoo | TSC Printer | Epson Printer |
Star Printer | Bixolon Printer | Honeywell Printer | Datamax Printer |
Thermal Print | Print Custom Labels | Print Shipping Labels | Warehouse Label |
Stock Label | Lot Label | Serial Label | Product Sticker | Barcode Label |
QR Code Label | Invoice Print | Delivery Order Print | Packing Slip Print |
Manufacturing Label | Inventory Label | Label Printer Integration |
Print Report | Document Printer | Print Directly without Downloading |
Cloud Print | Remote Printing | Multi-device Print | ERP Printing Solution |
CUPS Printer | Raw Print | ZPL Template | Label Generator | Label Designer |
Odoo Zebra Printer | Odoo Thermal Printer | Direct Print Label | Print Direct |
Odoo Print Automation | Odoo Label Creator | Barcode Label Print |
QZ Tray Base | QZ Tray Connector | QZ Tray Integration | QZ Tray ZPL |
Label Printing via QZ Tray | Odoo QZ Tray Printing | Direct ZPL Printing |
Print Product Label | Print Stock Label | Sticker Printer | Network Label Printing |
USB Printer Odoo | Plug-and-play Print | Smart Print Solution |
Automated Printing | Print Workflow | Batch Print | Multi-Label Printing |
Dymo Printer | Brother Printer | DHL Label | FedEx Label | UPS Label |
USPS Label | GLS Label | Shipping Label Printing from Odoo

Author: Steven Marp
    """,
    "author": "Steven Marp",
    "website": "https://apps.odoo.com/apps/browse?repo_maintainer_id=512936",
    "category": "Productivity",
    "license": "OPL-1",
    "depends": ["base", "mail", "web", "product"],
    "data": [
        # Security
        "security/direct_print_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/label_templates.xml",
        # Views
        "views/printer_views.xml",
        "views/label_template_views.xml",
        "views/print_job_views.xml",
        "views/menu.xml",
        # Wizard
        "wizard/print_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sm_direct_print/static/lib/qz-tray.js",
            "sm_direct_print/static/src/js/direct_print_action.js",
            "sm_direct_print/static/src/js/print_dashboard.js",
            "sm_direct_print/static/src/js/label_preview.js",
            "sm_direct_print/static/src/xml/direct_print_templates.xml",
            "sm_direct_print/static/src/xml/print_dashboard.xml",
            "sm_direct_print/static/src/xml/label_preview.xml",
            "sm_direct_print/static/src/scss/print_dashboard.scss",
        ],
    },
    "images": ["static/description/banner.gif"],
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 149.00,
    "currency": "USD",
}
