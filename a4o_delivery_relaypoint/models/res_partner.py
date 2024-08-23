# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import api, models, fields, _
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"

    code_relaypoint = fields.Char(index=True)
    point_type = fields.Char(index=True)
    latitude = fields.Char(string='Latitude')
    longitude = fields.Char(string='Longitude')

    def update_set_coordinates(self):
        # [TODO] Set the coordinate from the address data.
        pass