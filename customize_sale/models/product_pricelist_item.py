
from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _

class PriceListInherit(models.Model):
    _inherit = 'product.pricelist.item'

    product_code = fields.Char(string="Product Code", related="product_id.default_code")
