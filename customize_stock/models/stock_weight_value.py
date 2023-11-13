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

    move_line_id = fields.Many2one('stock.move.line', 'Move line')

    state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('done', 'Done'), ('simulation', 'simulation')],
                             string='Status', default="draft")
