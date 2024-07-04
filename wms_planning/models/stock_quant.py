# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse",
                                   related="location_id.warehouse_id", store=True)

