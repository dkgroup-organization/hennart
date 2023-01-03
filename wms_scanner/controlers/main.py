# -*- coding: utf-8 -*-

import logging

from odoo import http, models
from odoo.http import request


_logger = logging.getLogger(__name__)

SRC_PATH = 'wms_scanner'
IMG_PATH = SRC_PATH + '/static/src/img/'
CSS_FILE = SRC_PATH + "/static/src/css/screen_240.css"
IMG_FLAG = {'fr_FR': 'flag-fr.jpg', 'en_US': 'flag-gb.jpg', 'nl_BE': 'flag-be.jpg', 'de_DE': 'flag-de.jpg'}


class WmsController(http.Controller):

    @http.route(['/scanner'], type='http', auth='user', redirect='/web/login?redirect=%2Fscanner', csrf=False)
    def index(self, debug=False, **k):
        """ the main core of the scanner:

            - in first the possibility to have multiple session opened for a user, so 1 login for many scanner but only one session by scanner
            - in second a workflow analyse by session open, so a storage of data workflow by opened session.
            - in third a qweb render to return simple HTML page, so an internal odoo reading and accessing data,
            """

        # Check if user is logged
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=%2Fscanner')

        # Get session data
        data = self.get_session_data()

        # Analyse response, complete data
        data = self.analyse_response(data)

        # Function or Qweb render
        if data.get('function'):
            res = self.session_function(data)
        else:
            res = self.render_QWEB(data)

        # save session data
        self.save_session_data(data)
        return res

    def init_data(self):
        """ Initialize session data dictionary
        The data is saved in the request session dictionary
        It's the more simple, can be envolved to store in database to have nice management
        """
        request.session['session_data'] = {}
        data = {
            'user': request.env['res.users'].browse(request.uid),
            }
        return data

    def get_session_data(self):
        """ Get the data previously stored in session, restore the odoo object
        a named convention design an odoo object started by: model_
        after 'model_' add the name of the model the value is a tuple (model._name, ids)
        This named object store ids of this object
        """
        data = {}
        session_data = request.session.get('session_data', self.init_data())

        for data_key, data_value in session_data.items():
            if len(data_key) > 6 and data_key[:6] == "model_":
                # restore this odoo object
                data[data_key[6:]] = request.env[data_value[0]].browse(data_value[1])
            else:
                data[data_key] = data_value
        return data

    def save_session_data(self, data):
        """ save data by session, so one session data by scanner
        Some key is reserved for management scanner and not have to be saving:
        - qweb_template
        - function
        -

        """

        session_data = {}

        for key in list(data.keys()):
            if hasattr(data[key], '_name') and hasattr(data[key], 'ids'):
                # Odoo model name
                session_data['model_' + key] = (data[key]._name, data[key].ids)
            else:
                session_data.update({key: data[key]})

        request.session['session_data'] = session_data

    def analyse_response(self, data):
        "Analyse response"
        # get the scanner response
        response = dict(request.params) or {}

        if not response:
            # first time go to main menu
            data = self.main_menu()

        if response.get('menu'):
            if not response['menu'].isdigit() or response['menu'] <= '0':
                # main menu (menu=0) or not defined, go to main menu
                data = self.main_menu()
            else:
                # list the childs menus
                menu_ids = request.env['wms.menu'].search([('id', '=', int(response['menu']))])
                if menu_ids:
                    menu = menu_ids[0]
                    if menu.menu_type in ['wms', 'logout']:
                        # Return session_function
                        data['function'] = menu.menu_type
                    elif menu.menu_type == 'scanner':
                        data['qweb_template'] = 'wms_scanner.scanner_zxing2'
                    else:
                        # return childs menus
                        data['menu'] = request.env['wms.menu'].search([('parent_id', '=', menu.id)])
                else:
                    data = self.main_menu()

        elif response.get('scenario'):
            # Go to the scenario
            if not response['scenario'].isdigit() or response['scenario'] <= '0':
                # scenario not defined, go to main menu
                data = self.main_menu()
            else:
                scenario_ids = request.env['wms.scenario'].search([('id', '=', int(response['scenario']))])
                if scenario_ids:
                    data = scenario_ids[0].do_scenario(data)
                else:
                    # scenario not defined, go to main menu
                    data = self.main_menu()
        else:
            # To defined or some error
            data = self.main_menu()
        return data

    def main_menu(self):
        """ Return to main menu """
        data = self.init_data()
        data['menu'] = request.env['wms.menu'].search([('parent_id', '=', False)])
        return data

    def session_function(self, data):
        "Specific menu function"
        function_name = data.get('function', '?')

        if function_name == 'wms':
            # Return to Odoo
            return request.redirect(location='/web')

        elif function_name == 'logout':
            # Return to login page
            request.session.logout()
            return request.redirect(location='/web')

        else:
            # To defined or some error
            request.session.logout()
            return request.redirect(location='/web')

    def session_logout(self, data):
        "close the session, log information"
        request.session.logout()
        return request.redirect(self, '/web/login?redirect=%2Fscanner')

    def session_debug(self, data):
        "Debug information, return data in html"
        debug = "<b>DATA:</b><br/>" + self.format_debug(data)
        return debug

    def format_debug(self, sub_data):
        "Debug information, return sub_data in html"
        if not sub_data:
            html = ""
        if type(sub_data) is dict:
            html = "<ul>"
            for key in list(sub_data.keys()):
                if type(sub_data[key]) in [list, dict]:
                    html += '<li><b>%s: </b></li>' % (key)
                    html += self.data_debug(sub_data[key])
                else:
                    html += '<li><b>%s: </b>%s</li>' % (key, sub_data[key])
            html += "</ul>"

        elif type(sub_data) is list:
            html = "<ul>"
            for idx, item in enumerate(sub_data):
                if type(item) in [list, dict]:
                    html += '<li>[%s]:</li>' % (idx)
                    html += self.data_debug(item)
                else:
                    html += '<li>[%s]: %s</li>' % (idx, item)
            html += "</ul>"

        else:
            html = "<li>%s</li>" % (sub_data)
        return html

    def render_QWEB(self, data):
        """ Use Qweb to render the page"""

        if data.get('qweb_template'):
            return request.render(data['qweb_template'], data)
        elif data.get('menu'):
            return request.render('wms_scanner.wms_scanner_menu_template', data)
        elif data.get('scenario'):
            try:
                res = request.render('wms_scanner.wms_scanner_scenario_template', data)
            except:
                data = {'debug': self.session_debug(data)}
                return request.render('wms_scanner.scanner_scenario_blank', data)
            return res
        else:
            return request.render('wms_scanner.scanner_scenario_blank', data)
