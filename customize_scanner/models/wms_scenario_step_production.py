# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo import models, api, fields, _
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.http import request
import time
import random
import datetime


class WmsScenarioStep(models.Model):
    _inherit = 'wms.scenario.step'

    def get_list_option(self, data):
        """ Return list of option of select input """
        self.ensure_one()
        res = []
        product = data.get('product_id')
        if product and self.action_variable == 'maturity_product_id':
            res.append((f'{product.id}', f'[{product.default_code}] {product.name}'))
            if product.gestion_affinage:
                list_maturity_product = product.get_maturity_product()
                for maturity_product in list_maturity_product[product.id]:
                    product_name = f'[{maturity_product.default_code}] {maturity_product.name}'
                    res.append((f'{maturity_product.id}', product_name))
        return res
