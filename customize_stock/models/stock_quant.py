from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    blocked = fields.Boolean('Blocked', compute="compute_blocked", store=True)
    producted = fields.Boolean('producted', related="lot_id.producted", store=True)
    product_categ_id = fields.Many2one(related='product_tmpl_id.categ_id', store=True)
    total_weight = fields.Float('Total Weight', compute='compute_total_weight')

    @api.depends('location_id.blocked', 'lot_id.blocked', 'lot_id.producted')
    def compute_blocked(self):
        """ Block the reservation of a quant"""
        for quant in self:
            if quant.lot_id.blocked:
                quant.blocked = True
            elif quant.lot_id.producted:
                quant.blocked = False
            elif quant.location_id.blocked:
                quant.blocked = True
            elif quant.location_id.location_id.blocked:
                quant.blocked = True
            else:
                quant.blocked = False

    def compute_total_weight(self):
        """ get total weight """
        for quant in self:
            if quant.lot_id.unit_weight:
                total_weight = quant.lot_id.unit_weight * quant.quantity
            elif quant.lot_id.unit_price and quant.lot_id.kg_price:
                total_weight = quant.lot_id.unit_price / quant.lot_id.kg_price * quant.quantity
                quant.lot_id.unit_weight = quant.lot_id.unit_price / quant.lot_id.kg_price
            else:
                total_weight = quant.lot_id.product_id.weight * quant.quantity
            quant.total_weight = total_weight

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

    @api.model
    def unreserve_quantity(self):
        """ Unreserve quantity after error """
        sql = """
            select sq.product_id, sq.location_id, sq.lot_id, 
            sum(sq.reserved_quantity) as quant_reserved_qty, sum(sml.reserved_uom_qty) as move_reserved_qty
            from stock_quant sq, stock_move_line sml
            where sq.reserved_quantity > 0.0
            and sml.state not in ('cancel', 'done')
            and sq.product_id = sml.product_id
            group by sq.product_id, sq.location_id, sq.lot_id
            having sum(sq.reserved_quantity) != sum(sml.reserved_uom_qty) 
        """
        self.env.cr.execute(sql)
        result_sql = self.env.cr.fetchall()

        for row in result_sql:
            product_id = row[0]
            location_id = row[1]
            lot_id = row[2]
            quant_reserved_qty = row[3]
            move_reserved_qty = row[4]
            if quant_reserved_qty > move_reserved_qty:
                condition = [('product_id', '=', product_id), ('location_id', '=', location_id), ('lot_id', '=', lot_id)]
                quant_ids = self.env['stock.quant'].search(condition)
                sum_qty = quant_reserved_qty - move_reserved_qty
                for quant in quant_ids:
                    if quant.reserved_quantity >= sum_qty:
                        quant.sudo().reserved_quantity -= sum_qty
                        sum_qty = 0.0
                    else:
                        sum_qty -= quant.reserved_quantity
                        quant.sudo().reserved_quantity = 0.0
                    if sum_qty == 0.0:
                        break


