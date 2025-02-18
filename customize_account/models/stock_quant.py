# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import groupby


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    value = fields.Monetary('Value', compute='compute_value', groups='stock.group_stock_manager')

    @api.depends('lot_id.unit_weight', 'lot_id.unit_price', 'lot_id.kg_price', 'quantity')
    def compute_value(self):
        """ Compute the quant value with real lot data """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for quant in self:
            quant.currency_id = quant.company_id.currency_id

            if not quant.location_id or not quant.product_id or\
                    not quant.location_id._should_be_valued() or\
                    quant._should_exclude_for_valuation() or\
                    float_is_zero(quant.quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.value = 0
                continue

            elif quant.lot_id:
                quant.value = quant.lot_id.unit_price * quant.quantity
            else:
                quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).value_svl
                
