# -*- coding: utf-8 -*-

import logging

from odoo import http, models
from odoo.http import request
import markupsafe


_logger = logging.getLogger(__name__)


class WmsController(http.Controller):

    @http.route(['/scanner'], type='http', auth='user', redirect='/web/login?redirect=%2Fscanner', csrf=False)
    def index(self, debug=False, **k):
        """ the main core of the scanner:
            - in first the possibility to have multiple session opened for a user,
                    so 1 login for many scanner but only one session by scanner
            - in second a workflow analyse by session open, so a storage of data workflow by opened session.
            - in third a qweb render to return simple HTML page, so an internal odoo reading and accessing data,
            """

        # Check if user is logged
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=%2Fscanner')

        # Get session data
        session = request.env['wms.session'].get_session()
        data = session.get_data()

        # Analyse response, complete data, create qweb_data
        qweb_data = self.analyse_response(data)

        # Render QWEB to html
        res = self.render_QWEB(qweb_data)

        # save session data
        session.save_data(qweb_data.get('data', {}))

        # Return html response to client
        return res

    def init_qweb_data(self):
        """ Add standard information to data to send to qweb render"""
        qweb_data = {}
        qweb_data['user'] = request.env['res.users'].browse(request.uid)
        qweb_data['header_menu'] = request.env['wms.menu'].search([('parent_id', '=', False)])
        return qweb_data

    def main_menu(self):
        """ Return to main menu """
        qweb_data = self.init_qweb_data()
        qweb_data['menu'] = request.env['wms.menu'].search([('parent_id', '=', False)])
        return qweb_data

    def analyse_response(self, data):
        """Analyse response"""
        # get the scanner response
        qweb_data = self.init_qweb_data()
        response = dict(request.params) or {}

        if not response:
            # first time go to main menu
            qweb_data = self.main_menu()

        elif response.get('menu'):
            if not response['menu'].isdigit() or int(response['menu']) <= 0:
                # main menu (menu=0) or not defined, go to main menu
                qweb_data = self.main_menu()
            else:
                # list the childs menus
                menu_ids = request.env['wms.menu'].search([('id', '=', int(response['menu']))])
                if menu_ids:
                    menu = menu_ids[0]
                    # return childs menus
                    qweb_data['menu'] = request.env['wms.menu'].search([('parent_id', '=', menu.id)])
                else:
                    qweb_data = self.main_menu()

        elif response.get('scenario'):
            # Go to the scenario
            if not response['scenario'].isdigit() or int(response['scenario']) <= 0:
                # scenario not defined, go to main menu
                qweb_data = self.main_menu()
            else:
                scenario_ids = request.env['wms.scenario'].search([('id', '=', int(response['scenario']))])
                if scenario_ids:
                    qweb_data['data'] = scenario_ids[0].do_scenario(data)
                else:
                    # scenario not defined, go to main menu
                    qweb_data = self.main_menu()
        else:
            # To defined or some error
            qweb_data = self.main_menu()

        return qweb_data or {}

    def qweb_debug(self, data):
        "Debug information, return data in html"
        debug = "<div><b>DATA:</b><br/>" + self.format_debug(data) + "</div>"
        return markupsafe.Markup(debug)

    def format_debug(self, sub_data):
        "Debug information, return data in html"
        if not sub_data:
            html = ""
        if type(sub_data) is dict:
            html = "<ul>"
            for key in list(sub_data.keys()):
                if type(sub_data[key]) in [list, dict]:
                    html += '<li><b>%s: </b></li>' % (key)
                    html += self.format_debug(sub_data[key])
                else:
                    html += '<li><b>%s: </b>%s</li>' % (key, sub_data[key])
            html += "</ul>"

        elif type(sub_data) is list:
            html = "<ul>"
            for idx, item in enumerate(sub_data):
                if type(item) in [list, dict]:
                    html += '<li>[%s]:</li>' % (idx)
                    html += self.format_debug(item)
                else:
                    html += '<li>[%s]: %s</li>' % (idx, item)
            html += "</ul>"
        else:
            html = "<li>%s</li>" % (sub_data)
        return html

    def render_QWEB(self, qweb_data):
        """ Use Qweb to render the page"""

        if qweb_data.get('menu'):
            return request.render('wms_scanner.wms_scanner_menu_template', qweb_data)

        # Find the template to use, on step? on scenario
        data = qweb_data.get('data', {})

        if data.get('step') and data['step'].step_qweb:
            qweb_template = data['step'].step_qweb
        elif data.get('scenario') and data['scenario'].scenario_qweb:
            qweb_template = data['scenario'].scenario_qweb
        else:
            qweb_template = False

        if data.get('debug'):
            qweb_data |= {'debug': self.qweb_debug(data)}
            return request.render('wms_scanner.scanner_scenario_blank', qweb_data)
        elif qweb_template:
            return request.render(qweb_template, qweb_data)
        else:
            qweb_data |= {'debug': self.qweb_debug(data)}
            return request.render('wms_scanner.scanner_scenario_blank', qweb_data)
