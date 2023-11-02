# See LICENSE file for full copyright and licensing details.

import time
import logging
# import threading
from odoo import api, fields, models
from odoo.models import MAGIC_COLUMNS
from . import odoo_proxy
from . import synchro_data

_logger = logging.getLogger(__name__)


class BaseSynchroObjLine(models.Model):
    """Class to store object line in base synchro."""
    _name = "synchro.obj.line"
    _description = "Synchronized record"

    @api.model
    def _selection_target_model(self):
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]

    name = fields.Datetime(
        string='Date',
        required=True,
        default=lambda *args: time.strftime('%Y-%m-%d %H:%M:%S')
    )
    obj_id = fields.Many2one(
        'synchro.obj',
        string='Object',
        required=True,
        ondelete='SET DEFAULT',
        index=True
    )
    description = fields.Char('description')
    local_id = fields.Integer(string='Local ID', index=True)
    remote_id = fields.Integer(string='Remote ID', index=True)
    server_id = fields.Many2one(related='obj_id.server_id', store=True)
    model_id = fields.Integer(related='obj_id.model_id.id', store=True, index=True)

    todo = fields.Boolean('Todo')
    error = fields.Char("Error")
    update_date = fields.Datetime(string='Latest update')
    remote_write_date = fields.Datetime(string='Latest remote write')
    removed = fields.Boolean(default=False, string="Removed on remote")
    resource_ref = fields.Reference(string='Record', selection='_selection_target_model',
                                    compute='_compute_resource_ref')

    @api.depends('obj_id', 'local_id')
    def _compute_resource_ref(self):
        for line in self:
            model_name = line.obj_id.model_id.model or False
            if model_name:
                line.resource_ref = '%s,%s' % (model_name, line.local_id or 0)
            else:
                line.resource_ref = False

    @api.onchange('local_id', 'remote_id')
    def onchange_local_id(self):
        if self.local_id and self.remote_id:
            self.todo = False
        else:
            self.todo = True

    def update_values(self):
        """" Rewrite value"""
        group_obj = {}
        # group by object
        for line in self:
            if line.obj_id not in list(group_obj.keys()):
                group_obj[line.obj_id] = [line.remote_id]
            else:
                group_obj[line.obj_id].append(line.remote_id)

        for obj in list(group_obj.keys()):
            remote_values = obj.remote_read(group_obj[obj])
            obj.write_local_value(remote_values)
            _logger.info('synchro:\n%s' % remote_values)
