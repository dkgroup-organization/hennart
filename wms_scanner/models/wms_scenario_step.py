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
    _name = 'wms.scenario.step'
    _description = 'Step for scenario'
    _order = 'sequence'

    sequence = fields.Integer('sequence')
    name = fields.Char(
        string='Name', compute="compute_name",
        store=True)
    action_scanner = fields.Selection(
        [('no_scan', 'No scan'),
         ('scan_quantity', 'Enter quantity'),
         ('scan_text', 'Enter Text'),
         ('scan_model', 'Scan model'),
         ('scan_info', 'Scan search'),
         ],
        string="Scanner", default="no_scan", required=True)
    action_model = fields.Many2one('ir.model', string="Model to scan")
    action_variable = fields.Char(string='Input name', default='scan')
    action_message = fields.Char(string='Input Placeholder')
    step_qweb = fields.Char(
        string='QWEB Template',
        help="Use a specific QWEB template at this step")
    scenario_id = fields.Many2one(
        comodel_name='wms.scenario',
        string='Scenario',
        required=True,
        help='Scenario for this step.')
    out_transition_ids = fields.One2many(
        comodel_name='wms.scenario.transition',
        inverse_name='from_id',
        string='Outgoing transitions',
        help='Transitions which goes to this step.')
    in_transition_ids = fields.One2many(
        comodel_name='wms.scenario.transition',
        inverse_name='to_id',
        string='Incoming transitions',
        help='Transitions which goes to the next step.')
    python_code = fields.Text(
        string='Python code',
        help='Python code to execute.')
    scenario_notes = fields.Text(related='scenario_id.notes')

    @api.depends('sequence', 'action_scanner', 'action_variable')
    def compute_name(self):
        """ Compute the name of the step"""
        for step in self:
            name = "%s: " % (step.sequence)
            if step.action_scanner == 'scan_model':
                name += "scan %s " % (step.action_model.model or '?')
            else:
                name += "scan %s " % (step.action_scanner)

            if step.action_variable:
                name += "to var: %s " % (step.action_variable)
            step.name = name

    def get_scanner_response(self):
        "get the response of the scanner, only one scan by session"
        self.ensure_one()
        params = dict(request.params) or {}
        if self.action_variable and params.get(self.action_variable):
            scan = params.get(self.action_variable, '')
        else:
            scan = params.get('scan', '')
        return scan

    def read_scan(self, data={}):
        "Decode scan and return associated objects"
        self.ensure_one()
        action_scanner = self.action_scanner
        action_variable = self.action_variable
        action_model = self.action_model

        if action_scanner in ['no_scan']:
            return data

        def is_alphanumeric(scan):
            "check the scan string"
            res = True
            for scan_char in scan:
                if scan_char not in string.printable:
                    res = False
                    break
            return res

        scan = self.get_scanner_response()

        if not (scan and data):
            pass
        elif not scan:
            data['warning'] = _('The barcode is empty')
        elif not action_variable:
            data['warning'] = _('This scenario is currently under construction.'
                                'Some parameters are not set. (no scan variable)')
        elif not is_alphanumeric(scan):
            data['warning'] = _('The barcode is unreadable')
        elif action_scanner == 'scan_text':
            data[action_variable] = "%s" % (scan)
        elif action_scanner == 'scan_quantity':
            try:
                quantity = float(scan)
                data[action_variable] = quantity
            except:
                data['warning'] = _('Please, enter a numeric value')

        elif action_scanner in ['scan_model', 'scan_info']:
            models_ids = action_model
            if action_scanner == 'scan_info':
                models_ids = self.env['ir.model.fields'].search([('name', '=', 'barcode')]).mapped('model_id')

            for model_id in models_ids:
                action_model = self.env[model_id.model]
                list_fields = []
                for search_field in ['barcode', 'default_code']:
                    if hasattr(action_model, search_field):
                        condition = [(search_field, '=', scan)]
                        result_ids = action_model.search(condition)
                        if len(result_ids) == 1:
                            data[action_variable] = result_ids[0]
                            break
                        elif len(result_ids) > 1:
                            data = self.read_scan_duplicate(data)

                if data.get(action_variable):
                    break
            if not data.get(action_variable):
                data['warning'] = _('The barcode is unknow')
        else:
            data['warning'] = _('The barcode is unknow')
        return data

    def read_scan_duplicate(self, data):
        "Function to return value when the scan found duplicat object"
        self.ensure_one()
        if self.action_scanner != 'scan_info':
            data['warning'] = _('The barcode has multiples references')
        return data

    def execute_step(self, data):
        """ compute the step"""
        self.ensure_one()
        data = self.read_scan(data)
        if not data.get('warning'):
            data = self.execute_code(data)
            if not data.get('warning'):
                data = self.execute_transition(data)
        data = self.info_message(data)
        return data

    def info_message(self, data):
        """ compute message from scanner"""
        message = ''
        if self.action_scanner in ['scan_info']:
            scan_model = data.get(self.action_variable or 'scan')
            message = ""
            if hasattr(scan_model, '_name') and hasattr(scan_model, 'ids'):
                for scan_model_id in scan_model:
                    for field_name in ['default_code', 'barcode', 'name']:
                        if hasattr(scan_model_id, field_name):
                            message += "<p>%s </p>" % (getattr(scan_model, field_name))
                    message += "<br/>"
        if message:
            data['message'] = markupsafe.Markup(message)
        return data

    def execute_code(self, data={}):
        "Eval the python code"
        self.ensure_one()
        if self.python_code:
            localdict = {'data': data.copy()}
            safe_eval(self.python_code, localdict, mode="exec", nocopy=True)
            return localdict.get('data')
        else:
            return data

    def execute_transition(self, data):
        """ compute the step"""
        self.ensure_one()
        for transition in self.out_transition_ids:
            if not transition.condition:
                continue
            localdict = {'data': data.copy()}
            eval = safe_eval(transition.condition, localdict, mode="eval", nocopy=True)
            if eval:
                data['step'] = transition.to_id
                break
        return data

