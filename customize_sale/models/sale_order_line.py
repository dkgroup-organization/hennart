# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    weight = fields.Float('weight', compute="compute_uos")
    product_uos = fields.Many2one('uom.uom', compute="compute_uos")
    product_uos_qty = fields.Float('Sale Qty', compute="compute_uos")

    def _compute_customer_lead(self):
        """ The customer lead is more complexe in this project, It depend on location of customer """
        self.customer_lead = 0.0

    @api.depends('product_id', 'product_uom_qty', 'state')
    def compute_uos(self):
        """ compute the value of uos"""
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for line in self:
            if line.state in ['cancel', 'done']:
                continue
            if line.product_id:
                line.product_uos = line.product_id.uos_id
            else:
                line.product_uos = self.env.ref('uom.product_uom_unit')

            if line.product_id.type == 'service' or line.is_delivery or line.display_type or line.is_downpayment:
                line.weight = 0.0
                line.product_uos = line.product_uom
                line.product_uos_qty = line.product_uom_qty
            else:
                line.weight = line.product_id.weight * line.product_uom_qty
                if line.product_id.uos_id == uom_weight:
                    line.product_uos_qty = line.weight
                else:
                    line.product_uos_qty = line.product_uom_qty * line.product_id.package_quantity

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        res = self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uos_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )
        return res

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

