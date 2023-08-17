from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    total_weight = fields.Float(string="Total Weight", compute='_compute_total_weight')
    discount_unlocked = fields.Boolean(string='Discount Unlocked ?')

    @api.depends('order_line.weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(order.order_line.mapped('weight'))

    def _get_discount_product(self):
        self.ensure_one()

        discount_product = self.env['product.pricelist.discount'].search(
            [('partner_id', '=', self.partner_id.id)], order="logistical_weight DESC")

        if discount_product and 'no_discount' in discount_product.mapped('discount_choice'):
            return False

        if not discount_product:
            discount_product = self.env['product.pricelist.discount'].search(
                [('pricelist_id.id', '=', self.pricelist_id.id)], order="logistical_weight DESC")

        if discount_product:
            for discount in discount_product:
                if self.total_weight >= discount.logistical_weight:
                    return discount
        return False

    def _apply_discount_product(self, discount):
        self.ensure_one()
        discount_line = self.env['sale.order.line']
        discount_product_ids = self.env['product.pricelist.discount'].search(
            [('product_discount_id', '!=', False)]).mapped('product_discount_id')
        for line in self.order_line:
            if line.product_id in discount_product_ids:
                discount_line |= line

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

                if discount_line:
                    discount_line.update(line_values)
                else:
                    if self._origin.id:
                        line_values['order_id'] = self._origin.id
                        self.env['sale.order.line'].sudo().create(line_values)
                    else:
                        order_line = self.order_line.update(line_values)
                        self.order_line += order_line

            elif discount.discount_choice == 'pricelist_discount':
                self.pricelist_id = discount.reduced_pricelist_id
                discount = self._get_discount_product()
                if discount and discount.discount_choice == 'pricelist_discount':
                    self._apply_discount_product(discount)
                self._remove_discount_product()
                self._recompute_prices()
                self._check_discount()

    def _get_max_subtotal_tax(self):
        """ return subtotal and tax"""
        discount_product_ids = self.env['product.pricelist.discount'].search(
            [('product_discount_id', '!=', False)]).mapped('product_discount_id')

        subtotal_by_tax = {}

        for line in self.order_line:
            if line.product_id in discount_product_ids:
                continue

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

    def check_discount(self):
        """ Check discount before action confirm"""
        discount_product_ids = self.env['product.pricelist.discount'].search(
            [('product_discount_id', '!=', False)]).mapped('product_discount_id')
        discount_pricelist_ids = self.env['product.pricelist.discount'].search(
            [('reduced_pricelist_id', '!=', False)]).mapped('reduced_pricelist_id')

        for sale in self:
            check_line = {}
            for line in sale.order_line:
                if line.product_id in discount_product_ids:
                    key = str(line.product_id)
                    if key not in list(check_line.keys()):
                        check_line[key] = line
                        if sale.pricelist_id in discount_pricelist_ids:
                            raise ValidationError(_(
                                "There is a logistical discounts and a price list discount. Please, check this"))
                    else:
                        raise ValidationError(_(
                            "There are 2 lines with logistical discount. Please, group them:\n{}".format(
                                line.product_id.name)))

            if sale.discount_unlocked and sale.pricelist_id not in discount_pricelist_ids and not check_line:
                raise ValidationError(_(
                    "There is not logistical discounts. Please, check this"))
