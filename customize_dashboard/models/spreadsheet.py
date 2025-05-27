from odoo import models, fields

class Spreadsheet(models.Model):
    _inherit = 'spreadsheet.spreadsheet'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True
    )
