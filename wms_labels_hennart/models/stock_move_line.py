# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    label_code = fields.Char('Default code', compute="_compute_product_code")

    def _compute_product_code(self):
        """ return product code to print, check if there is kit"""
        for line in self:
            default_code = line.product_id.default_code or ''
            if line.move_id.bom_line_id:
                bom = line.move_id.bom_line_id.bom_id
                if bom.type == 'phantom':
                    default_code = bom.product_id.default_code
            line.label_code = default_code

    def print_label(self, printer=None):
        """ Print label """
        label_id = self.env['printing.label.zpl2'].search([('model_id.model', '=', self._name)])

        if printer and label_id:
            for line in self:
                label_id.print_label(printer, line)
