# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import models, api, fields
from odoo import _
from odoo.http import request
from odoo.tools.safe_eval import safe_eval
import logging
logger = logging.getLogger('wms_scanner')


class WmsScenario(models.Model):
    _inherit = 'wms.scenario'

    def button_save_xml(self):
        """ Save in xml format with base_module_record """
        self.ensure_one()
        search_condition = [('scenario_id', '=', self.id)]
        save_vals = {
            'search_condition': search_condition,
        }
        save_xml = self.env['base.module.data']
        res = save_xml.record_objects()
        return res

        