# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
import subprocess
import logging
import platform
import tempfile
import os

_logger = logging.getLogger(__name__)


class DirectPrinter(models.Model):
    _name = 'direct.printer'
    _description = 'Direct Thermal Printer'
    _order = 'is_default desc, name'

    name = fields.Char(string='Printer Name', required=True,
                       help='A friendly name for this printer (e.g., "Warehouse Label Printer", "Receipt Printer Front Desk")')
    device_name = fields.Char(string='Device Name', required=True,
                              help='Exact printer name as seen by the OS.\n'
                                   'Linux: CUPS name (run: lpstat -p)\n'
                                   'Windows: Printer name from Control Panel → Devices and Printers\n'
                                   'Network: IP:port (e.g., 192.168.1.100:9100)')
    printer_type = fields.Selection([
        ('qz_tray', 'QZ Tray (Browser → Local Printer)'),
        ('cups', 'CUPS (Server-side, Linux/Mac)'),
        ('network', 'Network (IP:Port, Raw Socket)'),
    ], string='Print Method', default='qz_tray', required=True,
       help='QZ Tray: Print from browser to user\'s local USB printer.\n'
            'CUPS: Print from server to server-attached printer.\n'
            'Network: Send raw data to printer IP:port (TCP 9100).')
    printer_language = fields.Selection([
        ('zpl', 'ZPL (Zebra)'),
        ('epl', 'EPL (Eltron)'),
        ('tspl', 'TSPL (TSC)'),
        ('cpcl', 'CPCL (Zebra Mobile)'),
        ('dpl', 'DPL (Datamax)'),
        ('escpos', 'ESC/POS (Epson, Receipt)'),
        ('raw', 'Raw Text'),
    ], string='Printer Language', default='zpl', required=True)
    dpi = fields.Selection([
        ('152', '152 DPI (6 dpmm)'),
        ('203', '203 DPI (8 dpmm)'),
        ('300', '300 DPI (12 dpmm)'),
        ('600', '600 DPI (24 dpmm)'),
    ], string='Print Resolution', default='203')
    label_width = fields.Integer(string='Label Width (mm)', default=100,
                                 help='Physical label width in millimeters')
    label_height = fields.Integer(string='Label Height (mm)', default=50,
                                  help='Physical label height in millimeters')
    is_default = fields.Boolean(string='Default Printer', default=False)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)
    print_job_ids = fields.One2many('direct.print.job', 'printer_id', string='Print Jobs')
    print_job_count = fields.Integer(compute='_compute_print_job_count', string='Print Jobs')
    last_print_date = fields.Datetime(string='Last Print', compute='_compute_last_print', store=True)
    note = fields.Text(string='Notes')

    @api.depends('print_job_ids')
    def _compute_print_job_count(self):
        for rec in self:
            rec.print_job_count = len(rec.print_job_ids)

    @api.depends('print_job_ids', 'print_job_ids.create_date')
    def _compute_last_print(self):
        for rec in self:
            last_job = self.env['direct.print.job'].search([
                ('printer_id', '=', rec.id)
            ], order='create_date desc', limit=1)
            rec.last_print_date = last_job.create_date if last_job else False

    @api.model
    def get_default_printer(self):
        """Get default printer for current company."""
        printer = self.search([
            ('is_default', '=', True),
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)
        if not printer:
            printer = self.search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True)
            ], limit=1)
        return printer

    def set_as_default(self):
        """Set this printer as default for current company."""
        self.ensure_one()
        self.search([
            ('is_default', '=', True),
            ('company_id', '=', self.env.company.id)
        ]).write({'is_default': False})
        self.is_default = True

    def action_test_print(self):
        """Send test label to printer."""
        self.ensure_one()
        test_code = self._generate_test_label()

        if self.printer_type == 'qz_tray':
            return {
                'type': 'ir.actions.client',
                'tag': 'sm_direct_print.print_action',
                'params': {
                    'raw_data': [test_code],
                    'printer_name': self.device_name,
                    'job_name': 'Test Print',
                    'printer_type': self.printer_type,
                },
            }
        else:
            self.send_raw(test_code)
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'Test Print', 'message': 'Test label sent!', 'type': 'success'}}

    def _generate_test_label(self):
        """Generate test label in the printer's language."""
        if self.printer_language == 'zpl':
            return (
                "^XA\n"
                "^FO50,50^A0N,40,40^FDDirect Print Test^FS\n"
                f"^FO50,110^A0N,25,25^FDPrinter: {self.name}^FS\n"
                f"^FO50,145^A0N,25,25^FDDevice: {self.device_name}^FS\n"
                "^FO50,190^BY2^BCN,80,Y,N,N^FD1234567890^FS\n"
                "^FO50,300^A0N,20,20^FDIf you see this, it works!^FS\n"
                "^XZ\n"
            )
        elif self.printer_language == 'escpos':
            # ESC/POS for receipt/thermal printers (Epson, Star, etc.)
            ESC = '\x1b'
            GS = '\x1d'
            return (
                f"{ESC}@"                    # Initialize
                f"{ESC}a\x01"                # Center align
                f"{ESC}E\x01"                # Bold ON
                f"Direct Print Test\n"
                f"{ESC}E\x00"                # Bold OFF
                f"Printer: {self.name}\n"
                f"Device: {self.device_name}\n"
                f"\n"
                f"{GS}k\x49\x0d1234567890128"  # Code128 barcode
                f"\n\n"
                f"If you see this, it works!\n"
                f"\n\n\n"
                f"{GS}V\x00"                 # Cut paper
            )
        elif self.printer_language == 'tspl':
            return (
                f"SIZE 100 mm, 50 mm\n"
                f"GAP 3 mm, 0 mm\n"
                f"CLS\n"
                f"TEXT 50,50,\"3\",0,1,1,\"Direct Print Test\"\n"
                f"TEXT 50,100,\"2\",0,1,1,\"Printer: {self.name}\"\n"
                f"TEXT 50,140,\"2\",0,1,1,\"Device: {self.device_name}\"\n"
                f"BARCODE 50,180,\"128\",80,1,0,2,2,\"1234567890\"\n"
                f"TEXT 50,280,\"2\",0,1,1,\"If you see this, it works!\"\n"
                f"PRINT 1\n"
            )
        elif self.printer_language == 'epl':
            return (
                f"N\n"
                f"A50,50,0,3,1,1,N,\"Direct Print Test\"\n"
                f"A50,100,0,2,1,1,N,\"Printer: {self.name}\"\n"
                f"A50,130,0,2,1,1,N,\"Device: {self.device_name}\"\n"
                f"B50,170,0,1,2,4,80,N,\"1234567890\"\n"
                f"A50,270,0,2,1,1,N,\"If you see this, it works!\"\n"
                f"P1\n"
            )
        else:
            return f"Direct Print Test\nPrinter: {self.name}\nDevice: {self.device_name}\n"

    def send_raw(self, raw_data):
        """Send raw print data to printer (server-side: CUPS or network)."""
        self.ensure_one()
        if self.printer_type == 'cups':
            return self._print_cups(raw_data)
        elif self.printer_type == 'network':
            return self._print_network(raw_data)
        else:
            raise UserError("QZ Tray printing must be handled client-side (JavaScript).")

    def _print_cups(self, raw_data):
        """Print via CUPS (Linux/Mac)."""
        try:
            process = subprocess.Popen(
                ['lp', '-d', self.device_name, '-o', 'raw'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=raw_data.encode('utf-8'))
            if process.returncode != 0:
                raise UserError(f"CUPS print failed: {stderr.decode('utf-8')}")
            _logger.info(f"CUPS print sent to {self.device_name}: {stdout.decode('utf-8')}")
            return True
        except FileNotFoundError:
            raise UserError("CUPS 'lp' command not found. Install CUPS first.")

    def _print_network(self, raw_data):
        """Print via raw TCP socket (network printer on port 9100)."""
        import socket
        device = self.device_name
        if ':' in device:
            host, port = device.rsplit(':', 1)
            port = int(port)
        else:
            host, port = device, 9100

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((host, port))
                s.sendall(raw_data.encode('utf-8'))
            _logger.info(f"Network print sent to {host}:{port}")
            return True
        except Exception as e:
            raise UserError(f"Network print failed: {e}\nCheck that {host}:{port} is reachable.")

    def action_view_print_jobs(self):
        """Open print job history for this printer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Print Jobs — {self.name}',
            'res_model': 'direct.print.job',
            'view_mode': 'list,form',
            'domain': [('printer_id', '=', self.id)],
            'context': {'default_printer_id': self.id},
        }
