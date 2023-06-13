from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    total_weight = fields.Float(compute='_compute_total_weight')

    discount_unlocked = fields.Boolean(string='Discount Unlocked ?')

    @api.depends('order_line.weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(order.order_line.mapped('weight'))

    def _get_discount_product(self):
        for order in self:

            discount_product = self.env['product.pricelist.discount'].search(
                [('partner_id', '=', self.partner_id.id)], order="logistical_weight DESC")
            if not discount_product:
                discount_product = self.env['product.pricelist.discount'].search(
                    [('pricelist_id.id', '=', order.pricelist_id.id)], order="logistical_weight DESC")

            if discount_product:
                for discount in discount_product:
                    if order.total_weight >= discount.logistical_weight:
                        return discount
            return False

    def _apply_discount_product(self, discount):
        if self.total_weight >= discount.logistical_weight:
            # raise UserError('test1')
            if discount.discount_choice == 'product_discount':
                product_id = discount.product_discount_id
                discount_percent = discount.logistical_discount
                max_subtotal_tax, subtotal = self._get_max_subtotal_tax()

                line_values = {
                    'order_id': self._origin.id,
                    'product_id': product_id.id,
                    'name': product_id.name,
                    'product_uom_qty': 1,
                    'price_unit': -1 * (subtotal * (discount_percent / 100)),
                }
                if max_subtotal_tax:
                    line_values['tax_id'] = [(6, 0, [max_subtotal_tax.id])]

                if self._origin.id:
                    line_values['order_id'] = self._origin.id
                    self.env['sale.order.line'].sudo().create(line_values)
                else:
                    order_line = self.order_line.update(line_values)
                    self.order_line += order_line
            elif discount.discount_choice == 'pricelist_discount':
                self.pricelist_id = discount.reduced_pricelist_id

    def _get_max_subtotal_tax(self):
        subtotal_by_tax = {}

        for line in self.order_line:
            tax = line.tax_id
            subtotal = line.price_subtotal
            if tax in subtotal_by_tax:
                subtotal_by_tax[tax] += subtotal
            else:
                subtotal_by_tax[tax] = subtotal

        if subtotal_by_tax:
            max_subtotal_tax = max(subtotal_by_tax, key=subtotal_by_tax.get)
            return max_subtotal_tax, subtotal_by_tax[max_subtotal_tax]
        else:
            return False, 0.0

    def _remove_discount_product(self):
        for line in self.order_line:
            if line.product_id.is_discount:
                line.unlink()

    @api.onchange('total_weight', 'pricelist_id', 'partner_id')
    def _check_discount(self):
        discount = self._get_discount_product()
        if discount:
            self.discount_unlocked = True
        else:
            self.discount_unlocked = False

    def call_discount_activation(self):
        discount = self._get_discount_product()
        if discount:
            self._remove_discount_product()
            self._apply_discount_product(discount)

