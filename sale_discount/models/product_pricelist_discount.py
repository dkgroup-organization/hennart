from odoo import fields, models, api, _

class PriceListDiscount(models.Model):
    _name = 'product.pricelist.discount'
    _description = "Discount in pricelist"

    date_start = fields.Date(string='Date de départ')
    date_end = fields.Date(string='Date de fin')
    name = fields.Char(string='Description')
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Liste de prix',
        )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        )
    logistical_weight = fields.Float(string='Poids')
    logistical_discount = fields.Float(string='Remise %')
    product_discount_id = fields.Many2one(
        'product.product',
        string='Code produit pour la remise',
        )

    discount_choice = fields.Selection(
        string='Methode',
        selection=[('pricelist_discount', 'Remise Liste de prix'),
                   ('product_discount', 'Remise article'),
                   ('no_discount', 'No discount')],
        default='no_discount'
    )

    reduced_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Liste de prix avec réduction',
        )
