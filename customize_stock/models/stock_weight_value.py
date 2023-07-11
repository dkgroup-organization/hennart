# -*- coding: utf-8 -*-
from odoo import fields, models, api


class StockWeightValue(models.Model):
    _name = "stock.weight.value"
    _description = "Weight value"

    name = fields.Char('Weighing number', index=True)
    date = fields.Datetime('date', default=lambda self: fields.Datetime.now())
    device_id = fields.Many2one('stock.weight.device', 'Weight Device', index=True)
    weight = fields.Float('Total Weight', digits='Stock Weight')
    tare = fields.Float('Tare Weight', digits='Stock Weight')




    type =  fields.Selection([('1', 'Type 1')], 'type')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float('Quantity', digits='Product Unit of Measure')
    prodlot_id = fields.Many2one('stock.lot', 'Production lot')
    user_prepa_id = fields.Many2one('res.users', 'Preparator')
    picking_id = fields.Many2one('stock.picking', 'Reference', index=True)

    state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('done', 'Done')],
                             string='Status', default="draft")
