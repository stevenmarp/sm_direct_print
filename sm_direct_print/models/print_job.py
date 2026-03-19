# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PrintJob(models.Model):
    _name = 'direct.print.job'
    _description = 'Print Job History'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    printer_id = fields.Many2one('direct.printer', string='Printer', ondelete='set null')
    template_id = fields.Many2one('direct.print.label.template', string='Label Template',
                                  ondelete='set null')
    user_id = fields.Many2one('res.users', string='Printed By',
                              default=lambda self: self.env.user)
    job_name = fields.Char(string='Job Name')
    model_name = fields.Char(string='Source Model')
    record_ids = fields.Char(string='Record IDs', help='Comma-separated list of record IDs')
    record_count = fields.Integer(string='Records')
    label_count = fields.Integer(string='Labels Printed')
    copies = fields.Integer(string='Copies per Label', default=1)
    state = fields.Selection([
        ('sent', 'Sent to Printer'),
        ('success', 'Printed Successfully'),
        ('error', 'Error'),
    ], string='Status', default='sent')
    error_message = fields.Text(string='Error Details')
    zpl_data = fields.Text(string='ZPL Data', help='Raw ZPL sent to printer (first label)')
    print_method = fields.Selection([
        ('qz_tray', 'QZ Tray'),
        ('cups', 'CUPS'),
        ('network', 'Network'),
    ], string='Print Method')
    duration_ms = fields.Integer(string='Duration (ms)', help='Time taken to send print job')
    ip_address = fields.Char(string='IP Address')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('job_name', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            date_str = rec.create_date.strftime('%Y-%m-%d %H:%M') if rec.create_date else ''
            rec.display_name = f"{rec.job_name or 'Print Job'} — {date_str}"

    @api.model
    def log_job(self, vals):
        """Create a print job log entry. Called from JS after printing."""
        return self.sudo().create(vals)

    @api.model
    def get_dashboard_data(self):
        """Get stats for the print dashboard."""
        today = fields.Date.today()
        jobs_today = self.search_count([('create_date', '>=', fields.Datetime.to_string(today))])
        jobs_week = self.search_count([
            ('create_date', '>=', fields.Datetime.to_string(
                fields.Date.subtract(today, days=7)))
        ])
        labels_today = sum(self.search([
            ('create_date', '>=', fields.Datetime.to_string(today))
        ]).mapped('label_count'))

        errors_today = self.search_count([
            ('create_date', '>=', fields.Datetime.to_string(today)),
            ('state', '=', 'error'),
        ])

        printers = self.env['direct.printer'].search_count([('active', '=', True)])
        templates = self.env['direct.print.label.template'].search_count([('active', '=', True)])

        # Recent jobs
        recent = self.search([], limit=20)
        recent_data = []
        for job in recent:
            recent_data.append({
                'id': job.id,
                'job_name': job.job_name or 'Print Job',
                'printer': job.printer_id.name if job.printer_id else '—',
                'user': job.user_id.name if job.user_id else '—',
                'label_count': job.label_count,
                'state': job.state,
                'date': job.create_date.strftime('%Y-%m-%d %H:%M') if job.create_date else '',
            })

        return {
            'jobs_today': jobs_today,
            'jobs_week': jobs_week,
            'labels_today': labels_today,
            'errors_today': errors_today,
            'printers': printers,
            'templates': templates,
            'recent_jobs': recent_data,
        }
