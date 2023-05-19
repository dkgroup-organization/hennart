

from odoo import _, api, fields, models
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_packaging = fields.Many2one(
        'product.packaging',
        string='Packaging',
        )

    prodlot_id = fields.Many2one(
        'stock.lot',
        string='Production lot',
        )
    
    lot = fields.Char()

    weight = fields.Float()

    weight_uom_id = fields.Many2one(
        'uom.uom',
        string='U',
        )
    
    cadeau = fields.Float(string='Remise Total')

    cost_price = fields.Float(string='Prix de revient')

    # discount = fields.Float(string='R %')

    discount1 = fields.Float(string='R1 %')

    discount2 = fields.Float(string='R2 %')

    margin = fields.Float(string='Marge total')

    margin_percent = fields.Float(string='Marge %')

    number_of_pack = fields.Float(string='Nb pack')

    number_of_unit = fields.Float(string='Nb unit')

    promotion = fields.Float(string='Promo %')
    
    uom_qty = fields.Float(string="Qty")

    type = fields.Char()

    initial_price = fields.Float(string='Price')

    histo_cost_price = fields.Float()

    product_uos = fields.Many2one('uom.uom', string="Udv")
    
    price_net = fields.Float(
        string='Prix net',
        compute='_compute_price_net'
    )

    @api.depends('price_unit', 'discount')
    def _compute_price_net(self):
        for line in self:
            line.price_net = line.price_unit - (line.price_unit * line.discount / 100)