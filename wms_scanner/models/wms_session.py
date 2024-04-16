# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
from odoo.http import request
import datetime

# Reserved variable term in data
DATA_RESERVED_NAME = ['user', 'warning', 'scan', 'function', 'message', 'button', 'result']


class WmsSession(models.Model):
    _name = "wms.session"
    _description = "Scanner session"
    _order = "start_date desc"

    def _default_warehouse(self):
        "find the user warehouse"
        return self.env['stock.warehouse'].search([])[0]

    name = fields.Char('Session', required=True, index=True)
    ip = fields.Char('IP', index=True)
    debug = fields.Boolean('Debug')
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')
    user_id = fields.Many2one('res.users', 'User')
    data = fields.Char('data')
    data_previous = fields.Char('Previous data')
    data_end = fields.Char('End data')
    menu_code = fields.Char('Menu code')
    request_method = fields.Char('Request metode')
    request_param = fields.Char('Request parameters')
    message = fields.Char('log last message')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', default=_default_warehouse)
    error = fields.Text('Error')

    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Done')],
        copy=False, index=True, readonly=True,
        default='draft')

    @api.model
    def get_reserved_var_name(self):
        """ retrun the list of reserved variable name """
        return DATA_RESERVED_NAME

    @api.model
    def get_session(self):
        """ return curent session data"""
        cookie_sid = request.httprequest.cookies.get('session_id')
        if not cookie_sid:
            return False
        session_ids = self.search([('name', '=', cookie_sid), ('state', '=', 'confirm')])
        if not session_ids:
            session_ids = self.create({
                'name': cookie_sid,
                'user_id': self.env.user.id,
                'start_date': fields.Datetime.now(),
                'state': 'confirm',
            })
        return session_ids[0]

    def save_data(self, data={}):
        """ save current session data in json format"""
        for session in self:
            session_data = {}
            session_message = {}
            session.data_end = str(data)

            for key in list(data.keys()):
                if not key:
                    continue
                elif key in DATA_RESERVED_NAME:
                    # Don't save this objects, juste log for debug
                    session_message.update({key: "{}".format(data[key])})
                elif '.' in key:
                    raise ValidationError(_("The name of the variable cannot contain dot:") + str(key))

                elif isinstance(data[key], (datetime.date, datetime.datetime)):
                    date_format = "%Y-%m-%d"
                    if isinstance(data[key], datetime.datetime):
                        date_format += " %H:%M:%S"
                    else:
                        date_format += " 00:00:00"
                    session_data['date.' + key] = data[key].strftime(date_format)

                elif hasattr(data[key], '_name') and hasattr(data[key], 'ids'):
                    # Odoo model name
                    session_data['model.' + key] = (data[key]._name, data[key].ids)

                else:
                    session_data.update({key: data[key]})

            session_data.update({'date.start_date': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            session.data = json.dumps(session_data)
            session.message = json.dumps(session_message)

    def init_data(self):
        """ Initialise data"""
        self.save_data({'user': self.env.user.id})

    def get_data(self):
        """ get current session data"""
        self.ensure_one()
        data = {}
        if not self.data:
            self.init_data()

        session_data = json.loads(self.data)

        self.request_method = request.httprequest.method
        self.request_param = dict(request.params)
        self.error = ''
        self.message = ''

        for data_key, data_value in session_data.items():
            if len(data_key) > 6 and data_key[:6] == "model.":
                # restore this odoo object
                data[data_key[6:]] = request.env[data_value[0]].browse(data_value[1])

            elif len(data_key) > 5 and data_key[:5] == "date.":
                # restore this date
                data[data_key[5:]] = fields.Datetime.from_string(data_value)
            else:
                data[data_key] = data_value

        self.data_previous = str(data)
        return data

    def test(self):
        """ test """
        vals = {'product_id': 25, 'location_id': 563, 'location_dest_id': 15, 'product_uom_qty': 1.0, 'product_uom': 1,
         'raw_material_production_id': 9, 'picking_type_id': 9, 'manual_consumption': True}
        self.env['stock.move'].create(vals)