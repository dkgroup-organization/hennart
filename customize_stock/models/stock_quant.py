
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    blocked = fields.Boolean('Blocked', compute="compute_blocked", store=True)

    @api.depends('location_id.blocked', 'lot_id.blocked')
    def compute_blocked(self):
        """ Block the reservation of a quant"""
        for quant in self:
            if quant.location_id.blocked:
                quant.blocked = True
            elif quant.lot_id.blocked:
                quant.blocked = True
            else:
                quant.blocked = False

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = [('product_id', '=', product_id.id), ('blocked', '!=', True)]
        if not strict:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND(
                [['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)] if lot_id else [('lot_id', '=', False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])
        return domain
