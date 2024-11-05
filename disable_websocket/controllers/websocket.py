# disable_websocket/controllers.py

from odoo.addons.bus.controllers.websocket import WebsocketController
from odoo.http import request, Response
from odoo import http

class DisableWebSocketController(WebsocketController):

    @http.route('/websocket', type="http", auth="public", cors='*', websocket=True)
    def websocket(self):
        """
        Overridden method to disable WebSocket connection by returning a simple response.
        """
        return Response("WebSocket disabled in development environment", status=200)
