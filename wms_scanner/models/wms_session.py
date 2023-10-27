# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import json
from odoo.http import request
import datetime

# Reserved variable term in data
DATA_RESERVED_NAME = ['user', 'warning', 'scan', 'function', 'message', 'button', 'result']


class WmsSession(models.Model):
    _name = "wms.session"
    _description = "Scanner session"
    _order = "write_date"

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
                if key in DATA_RESERVED_NAME:
                    # Don't save this objects, juste log for debug
                    session_message.update({key: "{}".format(data[key])})
                elif isinstance(data[key], (datetime.date, datetime.datetime)):
                    date_format = "%Y-%m-%d"
                    if isinstance(data[key], datetime.datetime):
                        date_format += " %H:%M:%S"
                    if data[key]:
                        session_data.update({key: data[key].strftime(date_format)})
                    #datetime.strptime(date_string, format)
                else:
                    if hasattr(data[key], '_name') and hasattr(data[key], 'ids'):
                        # Odoo model name
                        session_data['model.' + key] = (data[key]._name, data[key].ids)
                    else:
                        session_data.update({key: data[key]})

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
            else:
                data[data_key] = data_value

        self.data_previous = str(data)
        return data





