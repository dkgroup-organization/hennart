# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class StockWeightValue(models.Model):
    _name = "stock.weight.value"
    _description = "Weight value"

    name = fields.Char('Weighing number', index=True)
    date = fields.Datetime('date', default=lambda self: fields.Datetime.now())
    device_id = fields.Many2one('stock.weight.device', 'Weight Device', index=True)
    weight = fields.Float('Total Weight', digits='Stock Weight')
    tare = fields.Float('Tare Weight', digits='Stock Weight')

    move_line_id = fields.Many2one('stock.move.line', 'Move line')
    lot_id = fields.Many2one('stock.lot', 'Lot')

    state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('done', 'Done'), ('simulation', 'simulation')],
                             string='Status', default="draft")

    def get_weight(self):
        """ Return value to print on label """
        self.ensure_one()
        if self.weight:
            res = f"{self.weight:.3f} Kg"
        else:
            res = ''
        return res

    def get_label_weight(self):
        """ Return value to print on label """
        self.ensure_one()
        if self.weight:
            res = _("Net Weight:")
        else:
            res = ''
        return res

    def get_label_barcode(self):
        """ Add weight on label barcode """
        self.ensure_one()
        barcode = self.lot_id.barcode
        if self.weight and self.weight < 100.0:
            weight_label = f"{self.weight:.3f}".zfill(6)
            barcode = barcode[:-6] + weight_label
        return barcode
