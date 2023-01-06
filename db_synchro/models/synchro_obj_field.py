# See LICENSE file for full copyright and licensing details.

import time
import logging
# import threading
from odoo import api, fields, models
from odoo.models import MAGIC_COLUMNS
from . import odoo_proxy
from . import synchro_data

_logger = logging.getLogger(__name__)


class BaseSynchroObjField(models.Model):
    """Class Remote Fields."""
    _name = "synchro.obj.field"
    _description = "Remote Fields"

    name = fields.Char(
        string='Remote field name',
        required=True
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        string='local field',
        required=True,
        ondelete='cascade'
    )
    obj_id = fields.Many2one(
        'synchro.obj',
        string='Object',
        required=True,
    )

    #description = fields.Char('description')



    @api.onchange('field_id')
    def onchange_field(self):
        "return the name"
        self.name = self.field_id.name or ''

