from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime

class ResPartnerCadence(models.Model):
    _name = 'res.partner.cadence'
    _description = "Cadencier"


    partner_id = fields.Many2one('res.partner', 'Partner', index=True)
    product_id = fields.Many2one('product.product', 'product', index=True)
    default_code = fields.Char(related='product_id.default_code')
    week_number = fields.Integer('Week number', index=True)
    name = fields.Html(string="Cadencier", compute="compute_cadence", store=True, readonly=True, compute_sudo=True)
    order_name = fields.Char(related='product_id.name', store=True, index=True)

    _order = "order_name"

    @api.depends('product_id', 'week_number', 'partner_id')
    def compute_cadence(self):
        """ get the sale frequency of the product, futur function in customize_account"""
        for line in self:
            line.name = ' ... '

    @api.model
    def get_week_horizon(self):
        """ return horizon """
        return 13

    @api.model
    def get_week_number(self, date=None):
        """ return the number of week since the 02-01-2000 (first sunday of the millennium """
        date = date or datetime.datetime.now()
        if type(date) == datetime.datetime:
            date = date.date()
        debut = datetime.date(2000, 1, 2)
        delta = date - debut
        nb_week = int(delta.days // 7 + 1)
        return nb_week

