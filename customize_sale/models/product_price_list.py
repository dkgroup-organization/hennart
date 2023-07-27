
from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _

class PriceListInherit(models.Model):
    _inherit = 'product.pricelist'

    date_end = fields.Date(string="End Date")
    date_start = fields.Date(string="Start Date")

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
