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

    def button_save_xml(self, model_ids):
        """ Save in xml format with base_module_record """
        self.ensure_one()
        self.update_name()
        search_condition = [('scenario_id', '=', self.id)]
        save_vals = {
            'search_condition': search_condition,
            'filter_cond': 'all',
        }
        save_xml = self.env['base.module.data'].create(save_vals)
        save_xml.objects = model_ids
        res = save_xml.record_objects()
        return res

    def update_name(self):
        # Update name of step and transition to index the xml record
        for scenario in self:
            for step in scenario.step_ids:
                step.compute_name()
                for transition in step.out_transition_ids:
                    transition.compute_name()
