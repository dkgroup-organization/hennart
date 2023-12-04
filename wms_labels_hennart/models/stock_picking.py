
from odoo import models, fields ,api


class stock_picking(models.Model):
    _inherit = "stock.picking"

    label_type = fields.Selection(
        [('no_label', 'No label'), ('lot_label', 'Label all lots'), ('pack_lot', 'Label all packs')],
        default="lot_label", string="Label strategy")

    #label_line = fields.Many2one("")

    def create_package(self):
        """ Create package to label"""
        for picking in self:
            pass

    def print_container_label(self):
        """ Create package to label"""
        for picking in self:
            pass

    def action_confirm(self):
        """ Create Label of container"""

        for picking in self:
            pass

        return super(stock_picking,self).action_confirm()

