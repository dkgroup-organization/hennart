
from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _

class PriceListInherit(models.Model):
    _inherit = 'product.pricelist'

    date_end = fields.Date(string="End Date")
    date_start = fields.Date(string="Start Date")
