
from odoo import models
from odoo import fields ,api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sscc_lines_ids = fields.One2many('stock.sscc', 'picking_id', 'Code colis SSCC')
    nb_total_sscc = fields.Integer('Total label', compute='compute_total_sscc')

    @api.depends('sscc_lines_ids')
    def compute_total_sscc(self):
        """ return total label """
        for picking in self:
            picking.nb_total_sscc = len(picking.sscc_lines_ids)

    @api.depends('nb_container', 'nb_pallet')
    def update_sscc(self):
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue
            nb_total_container = picking.nb_container + picking.nb_pallet
            sscc_lines_ids = picking.sscc_lines_ids.mapped('id')
            todo_sscc = nb_total_container - len(sscc_lines_ids)
            if todo_sscc == 0:
                pass
            elif todo_sscc > 0:
                # Create SSCC
                while todo_sscc:
                    self.env['stock.sscc'].create({'picking_id': picking._origin.id})
                    todo_sscc -= 1
            elif todo_sscc < 0:
                # Delete SSCC
                while todo_sscc:
                    test = self.env['stock.sscc'].search([('picking_id', '=', picking._origin.id)],
                                                         order="id desc", limit=1)
                    test.unlink()
                    todo_sscc += 1
