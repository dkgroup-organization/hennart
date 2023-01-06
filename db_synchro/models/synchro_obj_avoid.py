# See LICENSE file for full copyright and licensing details.

import time
import logging
# import threading
from odoo import api, fields, models
from odoo.models import MAGIC_COLUMNS
from . import odoo_proxy
from . import synchro_data

_logger = logging.getLogger(__name__)


class BaseSynchroObjAvoid(models.Model):
    """Class with the fields of synchro object."""
    _name = "synchro.obj.avoid"
    _description = "Fields to synchronize"

    name = fields.Char(
        string='Remote Name',
        required=True
    )
    remote_type = fields.Char(
        string='Remote Type'
    )
    obj_id = fields.Many2one(
        'synchro.obj',
        string='Object',
        required=True,
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        string='local field',
        required=True,
        ondelete='cascade'
    )
    synchronize = fields.Boolean('synchronyse')
    check_remote = fields.Boolean('Remote checking')

    def button_synchronize(self):
        "to synchronize"
        for obj_avoid in self:
            obj_avoid.synchronize = True

    def button_unsynchronize(self):
        "to synchronize"
        for obj_avoid in self:
            obj_avoid.synchronize = False

