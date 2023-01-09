# See LICENSE file for full copyright and licensing details.

import time
import logging
import json
from odoo import api, fields, models
from odoo.models import MAGIC_COLUMNS
from . import odoo_proxy
from . import synchro_data

_logger = logging.getLogger(__name__)


class BaseSynchroObjField(models.Model):
    """Class Remote Fields."""
    _name = "synchro.obj.field"
    _description = "Remote Fields not linking"

    name = fields.Char(
        string='Remote field name',
        required=True
    )
    local_field_id = fields.Many2one(
        'synchro.obj.avoid',
        string='local field',
    )
    obj_id = fields.Many2one(
        'synchro.obj',
        string='Object',
        required=True,
    )

    description = fields.Char('description')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_create', 'To create'),
        ('to_link', 'To link'),
        ('not_used', 'Not used'),
        ('cancel', 'Cancelled')
        ], string='State', index=True, default='draft')



