from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    blocked = fields.Boolean('Blocked', compute="compute_blocked", store=True)
    product_categ_id = fields.Many2one(related='product_tmpl_id.categ_id', store=True)

    @api.depends('location_id.blocked', 'lot_id.blocked')
    def compute_blocked(self):
        """ Block the reservation of a quant"""
        for quant in self:
            if quant.location_id.blocked:
                quant.blocked = True
            if quant.location_id.location_id.blocked:
                quant.blocked = True
            elif quant.lot_id.blocked:
                quant.blocked = True
            else:
                quant.blocked = False

    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                  strict=False):
        """ Remove constraint to unreserve more quantity than there is in stock.
        because when a quant is unlinked , the picking is blocked
        it 's not possible to cancel it.
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict)

        if float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                if quantity > 0.0:
                    quantity = available_quantity
                else:
                    quantity = - available_quantity
        res = super()._update_reserved_quantity(product_id, location_id, quantity,
                                                lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        return res

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        """ Remove blocked location of the domain used to search reserved product """

        domain = [('product_id', '=', product_id.id)]
        if not strict:
            domain = expression.AND([[('blocked', '!=', True)], domain])
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND(
                [[('lot_id', '=', lot_id.id)] if lot_id else [('lot_id', '=', False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])
        return domain
