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
    _name = 'wms.scenario'
    _description = 'Scenario for scanner'
    _order = 'sequence'

    name = fields.Char(
        string='Name',
        required=True,
        translate=False,)
    sequence = fields.Integer(
        string='Sequence',
        default=100,
        required=False,
        help='Sequence order.')
    scenario_image = fields.Char(
        string='Image filename',
        default='construction.jpg')
    scenario_qweb = fields.Char(
        string='QWEB Template')
    scenario_title = fields.Char(
        string='QWEB Title', translate=True)
    debug_mode = fields.Boolean(
        string='Debug mode')
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If check, this object is always available.')
    step_ids = fields.One2many(
        comodel_name='wms.scenario.step',
        inverse_name='scenario_id',
        string='Scenario',
        help='Step of the scenario.')
    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='scanner_scenario_warehouse_rel',
        column1='scenario_id',
        column2='warehouse_id',
        string='Warehouses',
        help='Warehouses for this scenario.')
    notes = fields.Text(
        string='Notes',
        help='Store different notes, date and title for modification, etc...')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.user.company_id.id,
        help='Company to be used on this scenario.')
    group_ids = fields.Many2many(
        comodel_name='res.groups',
        relation='scanner_scenario_res_groups_rel',
        column1='scenario_id',
        column2='group_id',
        string='Allowed Groups',
        default=lambda self: [self.env.ref('stock.group_stock_user').id])
    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='scanner_scenario_res_users_rel',
        column1='scenario_id',
        column2='user_id',
        string='Allowed Users')

    scenario_id = fields.Integer(
        string='technical field to filter', store=True, compute="get_scenario_id")

    def button_save_xml_step(self):
        """ Save xml step"""
        model_ids = self.env["ir.model"].search([("model", "in", ['wms.scenario', 'wms.scenario.step'])])
        res = self.button_save_xml(model_ids=model_ids)
        return res

    def button_save_xml_transition(self):
        """ Save xml step"""
        model_ids = self.env["ir.model"].search([("model", "=", 'wms.scenario.transition')])
        res = self.button_save_xml(model_ids=model_ids)
        return res

    def button_save_xml(self, model_ids):
        """ Save the scenario in xml"""
        pass

    def get_scenario_id(self):
        """ technical field used to filter multiple object in once domain"""
        for scenario in self:
            if scenario._origin.id:
                scenario.scenario_id = scenario._origin.id
            else:
                scenario.scenario_id = False

    def copy(self, default=None):
        default = default or {}
        default['name'] = _('Copy of %s') % self.name

        scenario_new = super(WmsScenario, self).copy(default)
        step_news = {}
        for step in self.step_ids:
            step_news[step.id] = step.copy(
                {'scenario_id': scenario_new.id}).id
        for trans in self.env['wms.scenario.transition'].search(
                [('scenario_id', '=', self.id)]):
            trans.copy({'from_id': step_news[trans.from_id.id],
                        'to_id': step_news[trans.to_id.id]})
        return scenario_new

    def do_scenario(self, data):
        "execute the scenario"
        self.ensure_one()
        data = self.init_scenario(data)
        data = data['step'].execute_step(data)
        return data

    def init_scenario(self, data):
        """ initiate data"""
        self.ensure_one()
        # init data if first time
        params = dict(request.params) or {}

        if ((not data.get('step')) or (params.get('step') == '0') or (not data)
                or data.get('scenario') != self):
            # start new scenario
            if self.step_ids:
                start_step = self.step_ids.search([
                    ('scenario_id', '=', self.id)], limit=1, order='sequence')
                data = {'scenario': self,
                        'step': start_step or self.step_ids[0],
                        'user': self.env.user}
            else:
                data = {'scenario': self}
                # There is no starting step
                warning = _("There is no step in this scenario")
                data.update({'warning': warning})
        return data
