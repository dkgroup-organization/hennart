
from odoo import models, fields ,api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def print_container_label(self):
        """ Create package to label"""
        for picking in self:
            print('---------print_container_label-----------', )
            picking.update_sscc()
            for line in picking.sscc_line_ids:
                line.print_label()


