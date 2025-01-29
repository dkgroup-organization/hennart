# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import groupby


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    unit_weight = fields.Float('Weight', compute='_compute_value', store=True)
    unit_price = fields.Monetary('Unit price', compute='_compute_value', store=True,
                                 groups='stock.group_stock_manager')

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ (Product.value_svl / Product.quantity_svl) * quant.quantity, i.e. average unit cost * on hand qty
        """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for quant in self:
            quant.currency_id = quant.company_id.currency_id


            if not quant.location_id or not quant.product_id or\
                    not quant.location_id._should_be_valued() or\
                    quant._should_exclude_for_valuation() or\
                    float_is_zero(quant.quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.value = 0
                quant.unit_price = 0.0
                quant.unit_weight = quant.product_id.weight
                continue

            quantity = quant.product_id.with_company(quant.company_id).quantity_svl
            if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.value = 0.0
                quant.unit_price = 0.0
                quant.unit_weight = quant.product_id.weight
                continue

            # Check if there is a lot_id
            if quant.lot_id:
                quant.value = quant.lot_id.unit_price * quant.quantity
                quant.unit_weight = quant.lot_id.unit_weight or quant.product_id.weight
            else:
                quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).value_svl / quantity
                quant.unit_weight = quant.unit_weight or quant.product_id.weight

