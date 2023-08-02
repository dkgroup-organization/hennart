

from odoo import _, api, fields, models
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_packaging = fields.Many2one(
        'product.packaging',
        string='Packaging',
        )

    prodlot_id = fields.Many2many(
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
    supplier_discount_type = fields.Selection(string="Type of supplier info",selection=[('discount','Cascade discount'),('add','Add discount')],default="discount")

    @api.onchange('product_id')
    def _compute_price_supplier_discount(self):
        for line in self:
            if line.move_type == 'in_invoice' and line.product_id:
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.quantity )
                if (seller):
                    line.discount1 = seller.discount1
                    line.discount2 = seller.discount2
                    line.initial_price = seller.base_price
                    line.supplier_discount_type = seller.type
                    if (seller.product_name):
                        line.name = seller.product_name
                    if (seller.product_uos):
                        line.product_uos = seller.product_uos
                    else:
                        line.product_uos = line.product_id.uom_po_id
                else:
                    line.discount1 = line.discount2 = line.initial_price = 0.0
                    line.product_uos = line.product_id.uom_po_id

    @api.onchange('supplier_discount_type','discount1','discount2','initial_price')
    def _get_price(self):
        for rec in self:
            if (rec.initial_price > 0.0 and (rec.discount1 > 0.0 or rec.discount2 > 0.0)):
                if rec.supplier_discount_type == 'add':
                    rec.price_unit = rec.initial_price * (1 - ((rec.discount1 + rec.discount2) / 100.0))
                else:
                    rec.price_unit = rec.initial_price * (1 - (rec.discount1 / 100.0)) * (1 - (rec.discount2 / 100.0))
