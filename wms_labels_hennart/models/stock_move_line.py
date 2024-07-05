# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    label_code = fields.Char('Default code', compute="_compute_product_code")
    weight_label_value = fields.Char('Weight value on label', compute='compute_weight_label_value')
    weight_label = fields.Char('Weight label', compute='compute_weight_label_value')
    label_qty = fields.Integer('Nb of label to print', compute='compute_weight_label_value')

    @api.depends('pack_product_id', 'product_id')
    def _compute_product_code(self):
        """ return product code to print, check if there is kit"""
        for line in self:
            picking = line.picking_id
            default_code = line.product_id.default_code or '?????'
            if line.pack_product_id and line.number_of_pack >= 1.0 and picking.label_type != 'product_label':
                default_code = line.pack_product_id.default_code
            line.label_code = default_code

    @api.depends('picking_id.label_type', 'qty_done')
    def compute_weight_label_value(self):
        """ Compute the weight value to write on label, depends on number of label """
        weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for line in self:
            if line.picking_id:
                label_type = line.picking_id.label_type
            else:
                label_type = 'no_picking'
                line.print_ok = False
                line.to_weight = False

            weight_label_value = line.weight
            label_qty = 1
            if label_type == 'no_label':
                label_qty = 0

            elif label_type == 'pack_label':
                if line.number_of_pack >= 1.0:
                    weight_label_value = line.weight / (line.number_of_pack or 1.0)
                    label_qty = int(line.number_of_pack)
                elif line.qty_done >= 1.0:
                    weight_label_value = line.weight / (line.qty_done or 1.0)
                    label_qty = int(line.qty_done)

            elif label_type == 'product_label':
                weight_label_value = line.weight / (line.qty_done or 1.0)
                label_qty = int(line.qty_done)

            elif label_type == 'weight_label':
                if line.product_id.to_label or line.pack_product_id.to_label:
                    label_qty = int(line.number_of_pack or line.qty_done)
                    weight_label_value = line.weight / float(label_qty or 1)

            elif label_type == 'no_picking':
                label_qty = 1
                weight_label_value = 0.0

            if line.product_id.uos_id == weight_uom:
                line.weight_label_value = f"{weight_label_value:.3f} Kg"
                line.weight_label = _("Net Weight:")
            else:
                line.weight_label_value = ''
                line.weight_label = ''

            line.label_qty = label_qty

    def print_label(self, printer=None, label_id=None):
        """ Print label """
        label_id = label_id or self.env['printing.label.zpl2'].search([('model_id.model', '=', self._name)])
        if printer and label_id:
            for line in self:
                if line.print_ok or line.to_weight:
                    continue
                if line.to_label:
                    label_qty = line.label_qty
                    while label_qty > 0:
                        label_id.print_label(printer, line)
                        label_qty -= 1
                    line.to_label = False
                    line.print_ok = True
