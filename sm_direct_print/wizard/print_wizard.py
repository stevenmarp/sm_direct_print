# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PrintWizard(models.TransientModel):
    _name = 'direct.print.wizard'
    _description = 'Direct Print Wizard'

    printer_id = fields.Many2one('direct.printer', string='Printer',
                                 domain=[('active', '=', True)])
    template_id = fields.Many2one('direct.print.label.template', string='Label Template')
    copies = fields.Integer(string='Copies', default=1)
    model_name = fields.Char(string='Model')
    record_ids_str = fields.Char(string='Record IDs')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Set default printer
        printer = self.env['direct.printer'].get_default_printer()
        if printer:
            res['printer_id'] = printer.id

        # Get active model and IDs from context
        ctx = self.env.context
        active_model = ctx.get('active_model', '')
        active_ids = ctx.get('active_ids', [])
        res['model_name'] = active_model
        res['record_ids_str'] = ','.join(str(i) for i in active_ids) if active_ids else ''

        # Find matching templates for this model
        if active_model:
            model_rec = self.env['ir.model'].search([('model', '=', active_model)], limit=1)
            if model_rec:
                template = self.env['direct.print.label.template'].search([
                    ('model_id', '=', model_rec.id), ('active', '=', True)
                ], limit=1)
                if template:
                    res['template_id'] = template.id
                    res['copies'] = template.copies or 1

        return res

    @api.onchange('template_id')
    def _onchange_template(self):
        if self.template_id:
            self.copies = self.template_id.copies or 1

    def action_print(self):
        """Generate ZPL and send to printer."""
        self.ensure_one()
        if not self.printer_id:
            raise UserError("Please select a printer.")
        if not self.template_id:
            raise UserError("Please select a label template.")
        if not self.record_ids_str:
            raise UserError("No records selected.")

        record_ids = [int(x) for x in self.record_ids_str.split(',') if x.strip()]
        if not record_ids:
            raise UserError("No records selected.")

        records = self.env[self.model_name].browse(record_ids)
        if not records.exists():
            raise UserError("Selected records not found.")

        # Override copies if set in wizard
        template = self.template_id
        orig_copies = template.copies
        if self.copies != template.copies:
            template = template.with_context(override_copies=self.copies)

        zpl_list = []
        for record in records:
            zpl = template._render_zpl(record)
            for _i in range(max(1, self.copies)):
                zpl_list.append(zpl)

        total_labels = len(records) * max(1, self.copies)

        # Log print job
        self.env['direct.print.job'].log_job({
            'printer_id': self.printer_id.id,
            'template_id': self.template_id.id,
            'job_name': f'{self.template_id.name} — {len(records)} records',
            'model_name': self.model_name,
            'record_ids': self.record_ids_str,
            'record_count': len(records),
            'label_count': total_labels,
            'copies': self.copies,
            'print_method': self.printer_id.printer_type,
            'zpl_data': zpl_list[0] if zpl_list else '',
        })

        if self.printer_id.printer_type == 'qz_tray':
            return {
                'type': 'ir.actions.client',
                'tag': 'sm_direct_print.print_action',
                'params': {
                    'raw_data': zpl_list,
                    'printer_name': self.printer_id.device_name,
                    'job_name': f'{self.template_id.name} — {total_labels} labels',
                    'printer_type': self.printer_id.printer_type,
                    'total_labels': total_labels,
                    'record_count': len(records),
                },
            }
        else:
            # Server-side: send all ZPL
            for zpl in zpl_list:
                self.printer_id.send_raw(zpl)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Print Sent',
                    'message': f'{total_labels} labels sent to {self.printer_id.name}',
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
