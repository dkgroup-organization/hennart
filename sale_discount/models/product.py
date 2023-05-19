from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SaleOrderInherit(models.Model):
    _inherit = 'product.template'


    is_discount = fields.Boolean(string='Is Discount ?')