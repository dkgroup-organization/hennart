

import logging
from odoo import http
from odoo.http import Controller, request, route
from odoo.addons.web.controllers.action import Action
from odoo.addons.web.controllers.utils import clean_action


_logger = logging.getLogger(__name__)

class Action(Action):

    @route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        Actions = request.env['ir.actions.actions']
        value = False
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                action = request.env.ref(action_id)
                assert action._name.startswith('ir.actions.')
                action_id = action.id
            except Exception:
                action_id = 0   # force failed read

        if not action_id:
            action_id = request.env.ref('base.action_open_website').id

        base_action = Actions.browse([action_id]).sudo().read(['type'])
        if base_action:
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report':
                request.update_context(bin_size=True)
            if additional_context:
                request.update_context(**additional_context)
            action = request.env[action_type].sudo().browse([action_id]).read()
            if action:
                value = clean_action(action[0], env=request.env)
        return value

