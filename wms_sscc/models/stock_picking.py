
import logging

from odoo import models, fields, api


_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    sscc_line_ids = fields.One2many('stock.sscc', 'picking_id', 'Code colis SSCC')
    nb_total_sscc = fields.Integer('Total label', compute='compute_total_sscc')

    # Container and pallet need a sscc number.
    nb_container = fields.Integer('Nb container')
    nb_pallet = fields.Integer('Nb pallet')

    @api.depends('sscc_line_ids')
    def compute_total_sscc(self):
        """ return total label """
        for picking in self:
            picking.nb_total_sscc = len(picking.sscc_line_ids)

    @api.depends('nb_container', 'nb_pallet')
    def update_sscc(self):
        for picking in self:

            if picking.picking_type_code != 'outgoing':
                continue
            nb_total_container = int(picking.nb_container + picking.nb_pallet)
            sscc_line_ids = picking.sscc_line_ids.mapped('id')
            todo_sscc = nb_total_container - len(sscc_line_ids)

            if todo_sscc > 0:
                # Create SSCC
                while todo_sscc:
                    self.env['stock.sscc'].create({'picking_id': picking._origin.id})
                    todo_sscc -= 1
            elif todo_sscc < 0:
                # Delete SSCC
                while todo_sscc:
                    sscc = self.env['stock.sscc'].search([('picking_id', '=', picking._origin.id)],
                                                         order="id desc", limit=1)
                    sscc.unlink()
                    todo_sscc += 1

            # Rechercher le type de package ayant le nom "Chronopost Custom Parcel"
            default_package_type = self.env['stock.package.type'].search([('name', '=', 'Chronopost Custom Parcel')], limit=1)
            for sscc in picking.sscc_line_ids:
                if not sscc.result_package_id:
                    sscc.result_package_id = self.env['stock.quant.package'].create({
                        'name': sscc.name,
                        'package_type_id': default_package_type.id,
                        'shipping_weight': picking.shipping_weight / float(len(picking.sscc_line_ids)),
                    })
