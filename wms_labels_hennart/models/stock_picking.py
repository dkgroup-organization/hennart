
from odoo import models, fields ,api


class stock_picking(models.Model):
    _inherit = "stock.picking"

    def print_container_label(self):
        """ Create package to label"""
        for picking in self:
            picking.update_sscc()
            for line in picking.sscc_lines_ids():
                line.print_label()


