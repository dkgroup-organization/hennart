# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import sys
import traceback
from odoo import models, api, fields, exceptions
from odoo import _
from odoo.tools.safe_eval import expr_eval
import logging
logger = logging.getLogger('wms_scanner')


class ScannerScenarioTransition(models.Model):
    _name = 'wms.scenario.transition'
    _description = 'Transition for scenario'
    _order = 'sequence'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(
        string='Name',
        compute="compute_name",
        help='Name of the transition.')
    sequence = fields.Integer(
        string='Sequence',
        default=0,
        help='Sequence order.')
    from_id = fields.Many2one(
        comodel_name='wms.scenario.step',
        string='From',
        required=True,
        help='Step which launches this transition.')
    to_id = fields.Many2one(
        comodel_name='wms.scenario.step',
        string='To',
        required=True,
        help='Step which is reached by this transition.')
    condition = fields.Char(
        string='Condition',
        required=True,
        default='True',
        help='The transition is followed only if this condition is evaluated '
             'as True.')
    scenario_id = fields.Many2one(
        comodel_name='wms.scenario',
        string='Scenario',
        required=False,
        related="from_id.scenario_id",
        store=True,
        readonly=True)

    @api.depends('from_id', 'to_id', 'condition')
    def compute_name(self):
        """ compute name"""
        for transition in self:
            transition.name = "[{} -> {}] {}".format(transition.from_id.sequence,
                                                 transition.to_id.sequence, transition.condition)
