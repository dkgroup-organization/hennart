
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Location(models.Model):
    _inherit = "stock.location"

    blocked = fields.Boolean('Blocked', help="Block the possibility of reserve the product in this location")

    def should_bypass_reservation(self):
        """ Add the locked location to bypass reservatoin """
        res = super().should_bypass_reservation()
        res = res or self.blocked
        return res