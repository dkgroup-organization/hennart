# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import groupby


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    value = fields.Monetary('Value', compute='_compute_value', store=False, groups='stock.group_stock_manager')
    currency_id = fields.Many2one('res.currency', compute='_compute_value', store=True,  groups='stock.group_stock_manager')
    uos_id = fields.Many2one('uom.uom', related='product_id.uos_id', string='Unit of Sale')
    partner_supplier_id = fields.Many2one('res.partner', string='Supplier', compute='get_partner_supplier')



    def get_partner_supplier(self):
        """ get supplier """
        for quant in self:
            if quant.lot_id.upstream_picking:
                quant.partner_supplier_id = quant.lot_id.upstream_picking[0].partner_id
            elif quant.lot_id.invoice_lot_line_ids:
                partner_supplier_id = False
                for line in quant.lot_id.invoice_lot_line_ids:
                    if line.move_type == 'in_invoice':
                        partner_supplier_id = line.account_move_line_id.move_id.partner_id
                        break
                quant.partner_supplier_id = partner_supplier_id
            else:
                quant.partner_supplier_id = False

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'lot_id.unit_weight', 'lot_id.unit_price', 'lot_id.kg_price', 'quantity')
    def _compute_value(self):
        """ Compute the quant value with real lot data """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        currency_id = self.env.company.currency_id

        for quant in self:
            quant.currency_id = quant.company_id.currency_id or currency_id

            if not quant.location_id or not quant.product_id or\
                    not quant.location_id._should_be_valued() or\
                    quant._should_exclude_for_valuation() or\
                    float_is_zero(quant.quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.sudo().value = 0

            elif quant.lot_id:
                quant.sudo().value = quant.lot_id.unit_price * quant.quantity

            else:
                quant.sudo().value = quant.quantity * (quant.product_id.current_cost_price or quant.product_id.average_cost_price)
