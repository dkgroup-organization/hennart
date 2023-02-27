# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import string
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo import models, api, fields, _
from odoo.http import request
from odoo.exceptions import MissingError, UserError, ValidationError

logger = logging.getLogger('wms_scanner')


class WmsScenarioStep(models.Model):
    _name = 'wms.scenario.step'
    _description = 'Step for scenario'

    name = fields.Char(
        string='Name',
        help='Name of the step.')
    action_scanner = fields.Selection(
        [('none', 'Not used'),
         ('scan_quantity', 'Enter quantity'),
         ('scan_text', 'Enter description'),
         ('scan_model', 'Scan model'),
         ],
        string="Scanner", default="none")
    action_model = fields.Many2one('ir.model', string="model")
    action_variable = fields.Char(string='Variable', default='scan')
    action_message = fields.Html(string='message')
    step_qweb = fields.Char(
        string='QWEB Template',
        help="Use a specific QWEB template at this step")
    scenario_id = fields.Many2one(
        comodel_name='wms.scenario',
        string='Scenario',
        required=True,
        ondelete='cascade',
        help='Scenario for this step.')
    out_transition_ids = fields.One2many(
        comodel_name='wms.scenario.transition',
        inverse_name='from_id',
        string='Outgoing transitions',
        ondelete='cascade',
        help='Transitions which goes to this step.')
    in_transition_ids = fields.One2many(
        comodel_name='wms.scenario.transition',
        inverse_name='to_id',
        string='Incoming transitions',
        ondelete='cascade',
        help='Transitions which goes to the next step.')
    python_code = fields.Text(
        string='Python code',
        help='Python code to execute.')
    scenario_notes = fields.Text(related='scenario_id.notes')

    def get_scanner_response(self):
        "get the response of the scanner, only one scanner by session"
        self.ensure_one()
        params = dict(request.params) or {}
        if self.action_variable:
            scan = params.get(self.action_variable, '')
        else:
            scan = params.get('scan', '')
        return scan

    def read_scan(self, data={}):
        "Decode scan and return associated objects"
        self.ensure_one()
        scan = self.get_scanner_response()

        def is_alphanumeric(scan):
            "check the scan string"
            res = True
            for scan_char in scan:
                if scan_char not in string.printable:
                    res = False
                    break
            return res

        if not scan:
            data['warning'] = _('The barcode is empty')
        elif not self.action_variable:
            data['warning'] = _('This scenario is currently under construction.'
                                'Some parameters are not set. (variable)')
        elif not is_alphanumeric(scan):
            data['warning'] = _('The barcode is unreadable')
        elif self.action_scanner == 'scan_text':
            data[self.action_variable] = "%s" % (scan)
        elif self.action_scanner == 'scan_quantity':
            try:
                quantity = float(scan)
                data[self.action_variable] = quantity
            except:
                data['warning'] = _('Please, enter a numeric value')
        elif self.action_scanner == 'scan_model':
            if self.action_model:
                list_field = list(dir(self.env[self.action_model.model]))
                for search_field in ['barcode', 'default_code', 'code', 'name']:
                    if search_field in list_field:
                        condition = [(search_field, '=', scan)]
                        result_ids = self.env[self.action_model.model].search(condition)
                        if len(result_ids) == 1:
                            data[self.action_variable] = result_ids[0].id
                            break
                        elif len(result_ids) > 1:
                            data = self.read_scan_duplicate(data)
                if not data.get(self.action_variable):
                    data['warning'] = _('The barcode is unknow')
            else:
                data['warning'] = _('This scenario is currently under construction.'
                                    'Some parameters are not set. (model)')
        else:
            data['warning'] = _('The barcode is unknow')

        return data

    def read_scan_duplicate(self, data):
        "Function to return value when the scan found duplicat object"
        return data

    def run(self, data={}):
        "Eval the python code"
        self.ensure_one()
        localdict = data.copy()
        safe_eval(self.python_code, localdict, mode="exec", nocopy=True)
        if '__builtins__' in localdict:
            localdict.pop('__builtins__')
        return localdict
