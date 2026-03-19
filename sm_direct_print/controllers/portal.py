# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class DirectPrintController(http.Controller):

    @http.route('/direct_print/preview', type='json', auth='user', methods=['POST'])
    def label_preview(self, zpl='', width=4, height=2, dpi='203'):
        """Generate label preview image using Labelary API.
        Returns base64 PNG image.
        """
        import urllib.request
        import base64

        if not zpl:
            return {'error': 'No ZPL data provided'}

        # Convert mm to inches for Labelary API
        width_in = round(float(width) / 25.4, 2)
        height_in = round(float(height) / 25.4, 2)

        url = f'http://api.labelary.com/v1/printers/{dpi}dpi/labels/{width_in}x{height_in}/0/'

        try:
            req = urllib.request.Request(url, data=zpl.encode('utf-8'))
            req.add_header('Accept', 'image/png')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            with urllib.request.urlopen(req, timeout=10) as resp:
                img_data = resp.read()
                return {
                    'image': base64.b64encode(img_data).decode('utf-8'),
                    'content_type': 'image/png',
                }
        except Exception as e:
            _logger.warning(f"Labelary API error: {e}")
            return {'error': str(e)}

    @http.route('/direct_print/log_job', type='json', auth='user', methods=['POST'])
    def log_print_job(self, **kwargs):
        """Log a print job from client-side (QZ Tray)."""
        vals = {
            'printer_id': kwargs.get('printer_id'),
            'template_id': kwargs.get('template_id'),
            'job_name': kwargs.get('job_name', 'Print Job'),
            'label_count': kwargs.get('label_count', 0),
            'state': kwargs.get('state', 'sent'),
            'error_message': kwargs.get('error_message'),
            'print_method': 'qz_tray',
            'duration_ms': kwargs.get('duration_ms', 0),
            'ip_address': request.httprequest.remote_addr,
        }
        # Remove None values
        vals = {k: v for k, v in vals.items() if v is not None}
        job = request.env['direct.print.job'].log_job(vals)
        return {'id': job.id}

    @http.route('/direct_print/dashboard', type='json', auth='user', methods=['POST'])
    def dashboard_data(self):
        """Get dashboard statistics."""
        return request.env['direct.print.job'].get_dashboard_data()

    @http.route('/direct_print/printers', type='json', auth='user', methods=['POST'])
    def get_printers(self):
        """Get list of printers for current company."""
        printers = request.env['direct.printer'].search([
            ('active', '=', True),
            ('company_id', '=', request.env.company.id),
        ])
        return [{
            'id': p.id,
            'name': p.name,
            'device_name': p.device_name,
            'printer_type': p.printer_type,
            'is_default': p.is_default,
        } for p in printers]
