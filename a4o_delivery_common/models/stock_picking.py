# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    date_status_check = fields.Datetime(string="Status check date",
        readonly=True,
        help="Date the status was checked and updated.")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_status = fields.Selection([
            ('not_relevant', 'Not Relevant'),
            ('preparation', 'Preparation'),
            ('deposited', 'Deposited'),
            ('in_progress', 'In Progres'),
            ('indetermined', 'Indeterminate, see details to find out'),
            ('done', 'Done'),
            ], string="Delivery Status", readonly=True, copy=False,
        default='not_relevant', compute='_compute_delivery_status',
        help="If 'In Progress', continue to check the status of the "
        "shipment with the carrier.")
    delivery_status_details = fields.Char(string='Delivery Status Details',
        readonly=True)

    @api.depends('delivery_status', 'move_line_ids')
    def _compute_delivery_status(self):
        for picking in self:
            method = getattr(
                picking,
                '%s_get_picking_status' % picking.delivery_type,
                None)
            if method:
                status, details = method()
                picking.delivery_status = status
                picking.delivery_status_details = details
            else:
                picking.delivery_status = 'not_relevant'
