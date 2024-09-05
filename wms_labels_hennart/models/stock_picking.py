
from odoo import models, fields ,api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def print_container_label(self, printer=None):
        """ Create package to label"""
        for picking in self:
            picking.update_sscc()
            if printer:
                picking.sscc_line_ids.print_label(printer=printer)

    def print_label(self, printer=None, label_id=None):
        """ Print label if information ready """
        for picking in self:
            if printer:
                picking.move_line_ids.print_label(printer=printer, label_id=label_id)
