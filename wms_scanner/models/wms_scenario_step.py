# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


import string
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo import models, api, fields, _
from odoo.http import request
from odoo.exceptions import MissingError, UserError, ValidationError
import markupsafe
from datetime import timedelta
import logging
logger = logging.getLogger('wms_scanner')

# Define standard name of variable to use. QWEB template and button react on this name
ACTION_VARIABLE = {
    'location_id': {'model': 'stock.location', 'type': 'Model'},
    'location_origin_id': {'model': 'stock.location', 'type': 'Model'},
    'location_dest_id': {'model': 'stock.location', 'type': 'Model'},
    'product_id': {'model': 'product.product', 'type': 'Model'},
    'product_dest_id': {'model': 'product.product', 'type': 'Model'},
    'maturity_product_id': {'model': 'product.product', 'type': 'Model'},
    'picking_id': {'model': 'stock.picking', 'type': 'Model'},
    'quantity': {'model': '', 'type': 'Float'},
    'tare': {'model': '', 'type': 'Float'},
    'lot_id': {'model': 'stock.lot', 'type': 'Model'},
    'weight': {'model': '', 'type': 'Float'},
    'printer': {'model': '', 'type': 'Model'},
    'weighting_device': {'model': '', 'type': 'Model'},
    'number_of_packages': {'model': '', 'type': 'Float'},
    'nb_container': {'model': '', 'type': 'Float'},
    'nb_pallet': {'model': '', 'type': 'Float'},
    'expiry_date': {'model': '', 'type': 'Date'}


}


class WmsScenarioStep(models.Model):
    _name = 'wms.scenario.step'
    _description = 'Step for scenario'
    _order = 'sequence'

    sequence = fields.Integer('sequence')
    name = fields.Char(
        string='index', compute="compute_name",
        store=True)
    description = fields.Char('Description')
    action_scanner = fields.Selection(
        [('start', 'Start, no scan'),
         ('routing', 'Routing, no scan'),
         ('no_scan', 'Message, no scan'),
         ('scan_quantity', 'Enter quantity'),
         ('scan_weight', 'Scan Weight'),
         ('scan_tare', 'Scan Weight tare'),
         ('scan_text', 'Enter Text'),
         ('scan_date', 'Scan Date'),
         ('scan_select', 'Scan Select'),
         ('scan_model', 'Scan model'),
         ('scan_info', 'Scan search'),
         ('scan_multi', 'Scan multi'),
         ],
        string="Scanner", default="no_scan", required=True)
    action_model = fields.Many2one('ir.model', string="Model to scan",
                                   help="Define the model used at this step.")
    action_variable = fields.Char(string='Variable', default='scan',
                                  help="Define a name for the result of the scan at this step ")
    action_message = fields.Char(string='Input Placeholder', translate=True)
    action_presentation = fields.Html('Screen presentation', translate=True)

    step_qweb = fields.Char(
        string='QWEB Template',
        help="Use a specific QWEB template at this step (optional).")
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
        string='Python code after form',
        help='Python code to execute after qweb.')
    python_code_before = fields.Text(
        string='Python code before',
        help='Python code to execute before qweb.')
    scenario_notes = fields.Text(related='scenario_id.notes')
    debug_mode = fields.Boolean('Mode debug', help='No try/except protection when there is code execution.')

    def init_data(self, data={}):
        """ reinit the data of this step"""
        new_data = {}
        new_data['step'] = data.get('step') or self
        new_data['scenario'] = new_data['step'].scenario_id
        return new_data

    @api.onchange('action_scanner')
    def weighting_device(self):
        """ defined standard variable """
        vals = {}
        if self.action_scanner == "scan_weight":
            vals['action_variable'] = "weighting_device"
        if self.action_scanner == "scan_quantity":
            vals['action_variable'] = "quantity"
        self.update(vals)

    @api.depends('sequence')
    def compute_name(self):
        """ Compute the name of the step"""
        for step in self:
            name = step.scenario_id.name
            step.name = f"{name}-{step.sequence}"

    @api.onchange('action_variable')
    def onchange_action_variable(self):
        """ Return formated action variable"""
        self.ensure_one()
        action_variable = self.action_variable
        action_variable = action_variable.strip().lower()

        for replace_char in [('-', '_'), (',', ' '), (';', ' '), ('   ', ' '), ('  ', ' '), ('  ', ' ')]:
            action_variable = action_variable.replace(replace_char[0], replace_char[1])
        self.action_variable = action_variable

    def get_scanner_response(self):
        "get the response of the scanner, only one scan by session"
        self.ensure_one()
        params = dict(request.params) or {}
        scan = params.get('scan', '')
        return scan

    def read_button(self, data):
        """" Get the button """
        self.ensure_one()
        params = dict(request.params) or {}
        if params.get('button'):
            data['button'] = params.get('button')

            if params.get('scan') and data['button'] in list(ACTION_VARIABLE.keys()):
                var_name = data['button']
                value = params.get('scan')
                if ACTION_VARIABLE[var_name]['type'] == 'Model' and value.isnumeric():
                    data[var_name] = self.env[ACTION_VARIABLE[var_name]['model']].search([('id', '=', int(value))])
                elif ACTION_VARIABLE[var_name]['type'] == 'Float':
                    try:
                        data[var_name] = float(value)
                    except ValueError:
                        pass
            elif params.get('scan'):
                data[data['button']] = params.get('scan')
        return data

    def read_scan(self, data={}):
        """Decode scan and return associated objects"""
        self.ensure_one()
        action_scanner = self.action_scanner
        action_variable = self.action_variable
        action_model = self.action_model

        def is_alphanumeric(scan):
            """check the scan string"""
            res = True
            for scan_char in scan:
                if scan_char not in string.printable:
                    res = False
                    break
            return res

        if action_scanner in ['start', 'no_scan', 'routing']:
            # No scan needed
            return data
        else:
            scan = self.get_scanner_response()

        if not (scan and data):
            pass
        elif scan == '' or not scan:
            data['warning'] = _('The barcode is empty')
        elif not action_variable:
            data['warning'] = _('This scenario is currently under construction.'
                                'Some parameters are not set. (no scan variable)')
        elif not is_alphanumeric(scan):
            data['warning'] = _('The barcode is unreadable')
        elif action_scanner == 'scan_text':
            data[action_variable] = "%s" % (scan)
        elif action_scanner == 'scan_select':
            if action_model and scan.isnumeric():
                select_ids = self.env[action_model.model].search([('id', '=', int(scan))])
                if select_ids:
                    data[action_variable] = select_ids
                else:
                    data['warning'] = _('Please, select a value')
            else:
                data[action_variable] = "%s" % (scan)
        elif action_scanner == 'scan_date':
            try:
                data[action_variable] = fields.Date.from_string(scan)
            except:
                data['warning'] = _('This date format is not valid')

        elif action_scanner in ['scan_quantity', 'scan_tare']:
            try:
                quantity = float(scan)
                if quantity >= 0.0:
                    data[action_variable] = quantity
                else:
                    data['warning'] = _('Please, enter a positive value')
            except:
                data['warning'] = _('Please, enter a numeric value')

        elif action_scanner in ['scan_weight', 'scan_multi']:
            data = self.scan_multi(data, scan, action_variable)

        elif action_scanner in ['scan_model', 'scan_info']:
            models_ids = action_model
            if action_scanner == 'scan_info':
                models_ids = self.env['ir.model.fields'].sudo().search([('name', '=', 'barcode')]).mapped('model_id')

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

            if action_scanner == "scan_info" and not data.get(action_variable):
                data = self.scan_multi(data, scan, action_variable)

            elif not data.get(action_variable) and not data.get('warning'):
                data['warning'] = _('The barcode is unknown')
        else:
            data['warning'] = _('The barcode is unknown')
        return data

    def scan_multi(self, data, scan, action_variable):
        """Function to return value when the scan is custom:
        This function need to be personalized by customer module"""
        self.ensure_one()
        return data

    def read_scan_duplicate(self, data):
        "Function to return value when the scan found duplicat object"
        self.ensure_one()
        if self.action_scanner != 'scan_info':
            data['warning'] = _('The barcode has multiples references')
        return data

    def execute_step(self, data):
        """ compute the step:
        there are 3 actions: scan - compute - choice next step"""

        self.ensure_one()
        original_data = data.copy()
        data = self.read_button(data)
        if not data.get('button') and self.action_scanner not in ['start', 'routing', 'no_scan']:
            data = self.read_scan(data)

        if not data.get('warning'):
            data = self.execute_code(data)

            if not data.get('warning'):
                data = self.execute_transition(data)
                if not data.get('warning') and data.get('step') and data['step'] != self and \
                        data['step'].action_scanner in ['start', 'routing']:
                    data = data['step'].execute_step(data)

        if data.get('debug'):
            logger.warning("\nDebug_data: {}".format(data))
            original_data['debug'] = data['debug']
            data = original_data.copy()

        elif data.get('warning'):
            # If warning, restore previous data.
            logger.warning("Warning_data: {}".format(data))
            original_data['warning'] = data.get('warning', '')
            data = original_data.copy()

        if data.get('step') and original_data.get('step') and data['step'] != original_data['step']:
            next_step = data.get('step')
            data = next_step.execute_code_before(data)

        message = self.info_message(data)
        if message:
            data["message"] = message

        return data

    def info_message(self, data):
        """ compute message from scanner"""
        message = ''
        if self.action_scanner in ['scan_info']:
            scan_model = data.get(self.action_variable or 'scan')
            message = ""
            if hasattr(scan_model, '_name') and hasattr(scan_model, 'ids'):
                field_list = []
                for scan_model_id in scan_model:

                    if scan_model_id._name in ['product.product', 'stock.lot']:

                        field_list = ['default_code', 'barcode', 'name']
                        if scan_model_id._name == 'product.product':
                            product = scan_model_id
                        else:
                            product = scan_model_id.product_id

                        stock_quants = self.env['stock.quant'].search([
                            ('product_id', '=', product.id),
                            ('location_id.usage', '=', 'internal'),
                            ('quantity', '>', 0)
                        ])

                        message += "<b>{}: </b>".format(_('Product'))
                        message += '<p class="mb-5 border-b-2 pb-5 border-gray-300">[%s] %s</p>' % (product.default_code, product.name)

                        for quant in stock_quants:
                            message += '<p class="mb-5"><b>Lieu:</b> %s <br/>' % quant.location_id.name
                            if quant.lot_id and quant.lot_id.expiration_date:
                                message += "<b>Lot:</b> %s - %s<br/>" % (
                                    quant.lot_id.ref, quant.lot_id.expiration_date.strftime("%d/%m/%Y"))
                            message += "<b>%s:</b> %s " % (_('Quantity'), quant.quantity)

                            if quant.lot_id:
                                scenario_id = data.get('scenario') and data['scenario'].id or 0
                                step_id = data.get('step') and data['step'].id or 0
                                href = f"./scanner?scenario={scenario_id}&amp;step={step_id}&amp;button=print_later&amp;scan={quant.lot_id.id}"
                                message += f'<a class="border border-gray-200 items-center rounded-lg pl-2" href="{href}" >Imprimer</a>'

                            message += "</p>"

                    elif scan_model_id._name == 'stock.location':
                        stock_quants = self.env['stock.quant'].search([
                            ('location_id', '=', scan_model_id.id),
                            ('quantity', '>', 0)
                        ])

                        message += '<b>%s:</b><p class="mb-5 border-b-2 pb-5 border-gray-300"> %s </p>' % (_('Location'),
                                                                                           scan_model_id.name)
                        for quant in stock_quants:
                            message += '<p class="mb-5"><b>[%s] %s</b><br/>' % (quant.product_id.default_code,
                                                                                 quant.product_id.name)
                            if quant.lot_id:
                                message += "%s: %s - %s<br/>" % (
                                    _('Lot'), quant.lot_id.ref, quant.removal_date.strftime("%d/%m/%Y"))
                            message += "<b> %s:</b> %s <br/>" % (_('Quantity'), quant.quantity)
                            message += "</p>"
                    else:
                        field_list = ['barcode', 'name']
                        message += "<p><b> %s </b></p>" % scan_model_id._description or scan_model_id._name
                        for field_name in field_list:
                            if hasattr(scan_model_id, field_name):
                                message += "<p> %s </p>" % (getattr(scan_model, field_name))
                        message += "<br/>"

        return markupsafe.Markup(message)

    def execute_code(self, data=None, python_code=None):
        """ Eval the python code """
        self.ensure_one()
        data = data or {}
        python_code = python_code or self.python_code or ''

        if python_code:
            localdict = {
                'step': self,
                'env': self.env,
                'data': data.copy()}

            if self.debug_mode or self.scenario_id.debug_mode:
                safe_eval(python_code, localdict, mode="exec", nocopy=True)
                data = localdict.get('data')
            else:
                try:
                    safe_eval(python_code, localdict, mode="exec", nocopy=True)
                    data = localdict.get('data')
                except Exception as e:
                    debug = _("This code generate an error: %s" % (python_code or ''))
                    data.update({'debug': debug})
                    session = self.env['wms.session'].get_session()
                    session.error = str(e)
                    logger.warning(e)

        return data or {}

    def execute_code_before(self, data={}):
        "Eval the python code"
        self.ensure_one()
        if data['step'].python_code_before:
            data = self.execute_code(data=data, python_code=data['step'].python_code_before)
        return data

    def execute_transition(self, data):
        """ compute the step"""
        self.ensure_one()
        # Check transition
        for transition in self.out_transition_ids:
            if not transition.condition:
                continue
            localdict = {'data': data.copy()}

            try:
                res_eval = safe_eval(transition.condition, localdict, mode="eval", nocopy=True)
                if res_eval:
                    data['step'] = transition.to_id
                    break
            except Exception as e:
                data['debug'] = _("this code generate a error: {}".format(transition.condition))
                session = self.env['wms.session'].get_session()
                session.error = str(e)
                logger.warning(e)

        if not data.get('warning') and self.action_scanner in ['routing', 'start'] and (
                not data.get('step') or data['step'] == self):
            data['debug'] = data.get('debug', '') + _('The program is frozen in step: {}'.format(self.name))

        return data

    def get_default_location(self, warehouse=None):
        """ Get default location like output input preparation production"""
        warehouse = warehouse or self.env.ref('stock.warehouse0')
        location_ids = self.env['stock.location']
        location_ids |= warehouse.wh_input_stock_loc_id
        location_ids |= warehouse.wh_output_stock_loc_id
        location_ids |= warehouse.wh_pack_stock_loc_id
        return location_ids

    def get_message(self, data):
        """ get message to display about this step"""
        self.ensure_one()
        res = "message to user"
        return res

    def get_button_option(self, data):
        """ futur function """
        return []