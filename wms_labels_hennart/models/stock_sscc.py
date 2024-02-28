# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class StockSSCC(models.Model):
    _inherit = 'stock.sscc'

    def print_label(self, printer=None, label_id=None):
        """ print zpl label """
        label_id = label_id or self.env['printing.label.zpl2'].search([('model_id.model', '=', self._name)])
        if printer and label_id:
            for sscc in self:
                label_id.print_label(printer, sscc)
                label_id.print_label(printer, sscc)


