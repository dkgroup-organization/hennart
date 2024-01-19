
from odoo import models, fields ,api


class stock_picking(models.Model):
    _inherit = "stock.picking"

    def print_container_label(self):
        """ Create package to label"""
        for picking in self:
            pass

