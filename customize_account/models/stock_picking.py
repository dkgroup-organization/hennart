# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """ Add some checking before validation """
        self.move_ids_without_package.check_line()
        self.move_ids_without_package.move_line_ids.filtered(lambda x: x.qty_done == 0.0).unlink()
        res = super().button_validate()
        canceled_move = self.move_ids_without_package.filtered(lambda x: x.state == 'cancel')
        canceled_move.sudo().move_line_ids.unlink()
        return res
