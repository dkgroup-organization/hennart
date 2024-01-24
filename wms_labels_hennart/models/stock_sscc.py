# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockSSCC(models.Model):
    _inherit = "stock.sscc"

    def print_label(self, printer=None, label_id=None):
        """ Print label """
        label_id = label_id or self.env['printing.label.zpl2'].search([('model_id.model', '=', self._name)])
        if printer and label_id:
            for line in self:
                label_id.print_label(printer, line)
