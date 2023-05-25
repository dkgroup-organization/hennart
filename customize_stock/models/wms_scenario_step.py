# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import string
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo import models, api, fields, _
from odoo.http import request
from odoo.exceptions import MissingError, UserError, ValidationError
import markupsafe

logger = logging.getLogger('wms_scanner')


class WmsScenarioStep(models.Model):
    _inherit = 'wms.scenario.step'

    def scan_multi(self, data, scan):
        """Function to return value when the scan is custom:
        lot production construction code
        5 char: product code
        7 char: stock.lot.id
        1 char: product code type
        6 char: expiration date
        6 char: weight
        """
        self.ensure_one()

        # Detect the old barcode (reference used by V7)
        




        return data
