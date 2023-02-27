# -*- coding: utf-8 -*-

import logging

from odoo import http, models
from odoo.http import request


_logger = logging.getLogger(__name__)

SRC_PATH = 'wms_scanner/static/src'
IMG_PATH = SRC_PATH + '/static/src/img/'
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
        session = self.env['wms.session'].get_session()
        data = session.get_data()

        # Analyse response, complete data
        data = self.analyse_response(data)

        # Function or Qweb render
        if data.get('function'):
            res = self.session_function(data)
        else:
            qweb_data = self.get_qweb_data()
            res = self.render_QWEB(data | qweb_data)

        # save session data
        session.save_data(data)
        return res

    def get_qweb_data(self):
        """ Add standard information to data"""
        # Add standard object
        qweb_data = {}
        qweb_data['user'] = request.env['res.users'].browse(request.uid)
        qweb_data['header_menu'] = request.env['wms.menu'].search([('parent_id', '=', False)])
        return qweb_data


    def analyse_response(self, data):
        "Analyse response"
        # get the scanner response
        response = dict(request.params) or {}

        if not response:
            # first time go to main menu
            data = self.main_menu()

        if response.get('function'):
            if response.get('function', '?') in ['wms', 'logout']:
                # Return session_function
                data['function'] = response.get('function')

        elif response.get('menu'):
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
        if data.get('menu'):
            return request.render('wms_scanner.wms_scanner_menu_template', data)

        # Find the template
        if data.get('qweb_template'):
            qweb_template = data.get('qweb_template')
        elif data.get('step') and data['step'].step_qweb:
            qweb_template = data['step'].step_qweb
        elif data.get('scenario'):
            qweb_template = data['scenario'].scenario_qweb
        else:
            qweb_template = ''

        if qweb_template:
            return request.render(qweb_template, data)
        else:
            data |= {'debug': self.session_debug(data)}
            return request.render('wms_scanner.scanner_scenario_blank', data)
