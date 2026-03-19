# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
import logging
import re

_logger = logging.getLogger(__name__)

# ZPL barcode type mapping
ZPL_BARCODE_TYPES = {
    'code128': ('^BCN', '^BY2'),
    'code39': ('^B3N', '^BY2'),
    'ean13': ('^BEN', '^BY2'),
    'upca': ('^BUN', '^BY2'),
    'qrcode': ('^BQN,2', ''),
    'datamatrix': ('^BXN', ''),
    'code128_small': ('^BCN', '^BY1'),
}


class LabelTemplate(models.Model):
    _name = 'direct.print.label.template'
    _description = 'Label Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    model_id = fields.Many2one('ir.model', string='Apply to Model',
                               ondelete='cascade',
                               help='Which Odoo model this template is for (e.g., product.product, stock.lot)')
    model_name = fields.Char(related='model_id.model', store=True, string='Model Name')
    label_width = fields.Integer(string='Label Width (mm)', default=100, required=True)
    label_height = fields.Integer(string='Label Height (mm)', default=50, required=True)
    dpi = fields.Selection([
        ('152', '152 DPI'), ('203', '203 DPI'), ('300', '300 DPI'), ('600', '600 DPI'),
    ], string='DPI', default='203', required=True)
    copies = fields.Integer(string='Copies per Label', default=1)
    darkness = fields.Integer(string='Print Darkness', default=15,
                              help='ZPL ~SD value: 0-30, higher = darker')
    element_ids = fields.One2many('direct.print.label.element', 'template_id', string='Label Elements')
    zpl_preview = fields.Text(string='ZPL Preview', compute='_compute_zpl_preview')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Html(string='Notes')

    # Smart defaults
    orientation = fields.Selection([
        ('normal', 'Normal (Portrait)'),
        ('rotated', 'Rotated 90° (Landscape)'),
    ], string='Orientation', default='normal')

    @api.depends('element_ids', 'label_width', 'label_height', 'dpi', 'darkness')
    def _compute_zpl_preview(self):
        for rec in self:
            try:
                rec.zpl_preview = rec._generate_zpl_sample()
            except Exception as e:
                rec.zpl_preview = f"Error: {e}"

    def _mm_to_dots(self, mm):
        """Convert mm to dots based on DPI."""
        dpmm = {'152': 6, '203': 8, '300': 12, '600': 24}
        return int(mm * dpmm.get(self.dpi, 8))

    def _generate_zpl_sample(self):
        """Generate sample ZPL with placeholder values."""
        sample_data = {
            'name': 'Sample Product',
            'default_code': 'PROD-001',
            'barcode': '1234567890128',
            'list_price': '99.99',
            'categ_id': type('obj', (object,), {'name': 'Category'})(),
            'qty_available': '100',
            'lot_name': 'LOT-2026-001',
        }
        return self._render_zpl(sample_data)

    def _render_zpl(self, data):
        """Render ZPL code from template elements and data dict.
        
        data can be a dict or a recordset. If recordset, fields are accessed via getattr.
        """
        self.ensure_one()
        w = self._mm_to_dots(self.label_width)
        h = self._mm_to_dots(self.label_height)

        zpl = "^XA\n"
        if self.darkness:
            zpl += f"^MD{self.darkness}\n"
        zpl += f"^PW{w}\n"
        zpl += f"^LL{h}\n"
        zpl += "^LH0,0\n"

        if self.orientation == 'rotated':
            zpl += "^POI\n"

        for elem in self.element_ids.sorted('sequence'):
            zpl += elem._render_zpl_element(data, self)

        zpl += "^XZ\n"
        return zpl

    def generate_zpl_for_records(self, records):
        """Generate list of ZPL strings for given recordsets.
        
        Returns: list of ZPL strings (one per label, considering copies)
        """
        self.ensure_one()
        zpl_list = []
        for record in records:
            zpl = self._render_zpl(record)
            for _i in range(max(1, self.copies)):
                zpl_list.append(zpl)
        return zpl_list

    def action_preview(self):
        """Open label preview dialog."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'sm_direct_print.label_preview',
            'params': {
                'template_id': self.id,
                'zpl': self._generate_zpl_sample(),
                'width': self.label_width,
                'height': self.label_height,
                'dpi': self.dpi,
            },
        }

    def action_print_test(self):
        """Print test label."""
        self.ensure_one()
        printer = self.env['direct.printer'].get_default_printer()
        if not printer:
            raise UserError("No default printer configured. Go to Direct Print → Printers.")
        zpl = self._generate_zpl_sample()
        return {
            'type': 'ir.actions.client',
            'tag': 'sm_direct_print.print_action',
            'params': {
                'raw_data': [zpl],
                'printer_name': printer.device_name,
                'job_name': f'Test: {self.name}',
                'printer_type': printer.printer_type,
                'template_id': self.id,
                'printer_id': printer.id,
            },
        }


class LabelElement(models.Model):
    _name = 'direct.print.label.element'
    _description = 'Label Template Element'
    _order = 'sequence, id'

    template_id = fields.Many2one('direct.print.label.template', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    element_type = fields.Selection([
        ('text', 'Text / Field'),
        ('barcode', 'Barcode'),
        ('qrcode', 'QR Code'),
        ('line', 'Line / Separator'),
        ('box', 'Box / Rectangle'),
        ('raw_zpl', 'Raw ZPL Code'),
    ], string='Type', required=True, default='text')

    # Position
    pos_x = fields.Integer(string='X (mm)', default=5, help='Horizontal position from left edge in mm')
    pos_y = fields.Integer(string='Y (mm)', default=5, help='Vertical position from top edge in mm')

    # Text options
    field_name = fields.Char(string='Field / Expression',
                             help='Field name (e.g., name, default_code, barcode) or '
                                  'Python expression like: record.name + " - " + str(record.list_price)')
    static_text = fields.Char(string='Static Text', help='Fixed text (used if Field is empty)')
    font_size = fields.Integer(string='Font Size', default=28)
    font_width = fields.Integer(string='Font Width', default=0, help='0 = auto, or specify in dots')
    bold = fields.Boolean(string='Bold')
    rotation = fields.Selection([
        ('N', 'Normal'), ('R', '90°'), ('I', '180°'), ('B', '270°'),
    ], string='Rotation', default='N')

    # Barcode options
    barcode_type = fields.Selection([
        ('code128', 'Code 128'),
        ('code128_small', 'Code 128 (Small)'),
        ('code39', 'Code 39'),
        ('ean13', 'EAN-13'),
        ('upca', 'UPC-A'),
        ('qrcode', 'QR Code'),
        ('datamatrix', 'DataMatrix'),
    ], string='Barcode Type', default='code128')
    barcode_height = fields.Integer(string='Barcode Height (dots)', default=80)
    barcode_show_text = fields.Boolean(string='Show Text Below', default=True)

    # Line/Box options
    line_width = fields.Integer(string='Width (mm)', default=50)
    line_height = fields.Integer(string='Height (mm)', default=0,
                                 help='0 for horizontal line, >0 for box')
    line_thickness = fields.Integer(string='Thickness (dots)', default=2)

    # Raw ZPL
    raw_zpl = fields.Text(string='Raw ZPL Code',
                          help='Direct ZPL commands. Use {field_name} for dynamic values.')

    def _get_value(self, data, template):
        """Get the display value for this element."""
        if self.static_text and not self.field_name:
            return self.static_text

        field_expr = self.field_name or ''
        if not field_expr:
            return ''

        # Try direct field access
        try:
            if hasattr(data, field_expr):
                val = getattr(data, field_expr)
                if hasattr(val, 'name'):  # relational field
                    return str(val.name or '')
                return str(val or '')
            elif isinstance(data, dict) and field_expr in data:
                val = data[field_expr]
                if hasattr(val, 'name'):
                    return str(val.name or '')
                return str(val or '')
        except Exception:
            pass

        # Try dot notation (e.g., categ_id.name)
        try:
            parts = field_expr.split('.')
            val = data
            for part in parts:
                if hasattr(val, part):
                    val = getattr(val, part)
                elif isinstance(val, dict):
                    val = val.get(part, '')
                else:
                    return field_expr  # return as static text
            return str(val or '')
        except Exception:
            pass

        # Try as Python expression
        try:
            result = safe_eval(field_expr, {'record': data, 'str': str, 'int': int, 'float': float})
            return str(result or '')
        except Exception:
            pass

        # Fallback: return field expression as static text
        prefix = self.static_text + ' ' if self.static_text else ''
        return prefix + field_expr

    def _render_zpl_element(self, data, template):
        """Render this element to ZPL code."""
        self.ensure_one()
        x = template._mm_to_dots(self.pos_x)
        y = template._mm_to_dots(self.pos_y)

        if self.element_type == 'text':
            return self._render_text(x, y, data, template)
        elif self.element_type in ('barcode', 'qrcode'):
            return self._render_barcode(x, y, data, template)
        elif self.element_type == 'line':
            return self._render_line(x, y, template)
        elif self.element_type == 'box':
            return self._render_box(x, y, template)
        elif self.element_type == 'raw_zpl':
            return self._render_raw(data, template)
        return ''

    def _render_text(self, x, y, data, template):
        value = self._get_value(data, template)
        if not value:
            return ''
        fs = self.font_size or 28
        fw = self.font_width or fs
        rot = self.rotation or 'N'
        zpl = f"^FO{x},{y}\n"
        zpl += f"^A0{rot},{fs},{fw}\n"
        zpl += f"^FD{value}^FS\n"
        return zpl

    def _render_barcode(self, x, y, data, template):
        value = self._get_value(data, template)
        if not value:
            return ''
        bc_type = self.barcode_type or 'code128'
        if bc_type == 'qrcode' or self.element_type == 'qrcode':
            bc_type = 'qrcode'

        bc_cmd, by_cmd = ZPL_BARCODE_TYPES.get(bc_type, ('^BCN', '^BY2'))
        bh = self.barcode_height or 80
        show = 'Y' if self.barcode_show_text else 'N'

        zpl = f"^FO{x},{y}\n"
        if by_cmd:
            zpl += f"{by_cmd}\n"

        if bc_type == 'qrcode':
            zpl += f"^BQN,2,5\n"
            zpl += f"^FDMA,{value}^FS\n"
        elif bc_type == 'datamatrix':
            zpl += f"^BXN,5,200\n"
            zpl += f"^FD{value}^FS\n"
        else:
            zpl += f"{bc_cmd},{bh},{show},N,N\n"
            zpl += f"^FD{value}^FS\n"
        return zpl

    def _render_line(self, x, y, template):
        w = template._mm_to_dots(self.line_width) or 100
        t = self.line_thickness or 2
        return f"^FO{x},{y}^GB{w},{t},{t}^FS\n"

    def _render_box(self, x, y, template):
        w = template._mm_to_dots(self.line_width) or 100
        h = template._mm_to_dots(self.line_height) or 50
        t = self.line_thickness or 2
        return f"^FO{x},{y}^GB{w},{h},{t}^FS\n"

    def _render_raw(self, data, template):
        raw = self.raw_zpl or ''
        # Replace {field_name} placeholders
        def replacer(match):
            fname = match.group(1)
            try:
                if hasattr(data, fname):
                    return str(getattr(data, fname) or '')
                elif isinstance(data, dict):
                    return str(data.get(fname, ''))
            except Exception:
                pass
            return match.group(0)
        return re.sub(r'\{(\w+)\}', replacer, raw) + '\n'
