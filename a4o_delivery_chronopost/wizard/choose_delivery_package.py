# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import models


class ChooseDeliveryPackage(models.TransientModel):
    _description = 'Delivery Package Selection Wizard'
    _inherit = 'choose.delivery.package'

    def chronopost_compute_mandatory_weight(self):
        return True
