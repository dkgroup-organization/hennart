# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging
log = logging.getLogger(__name__).info

class AccountMoveImportLine(models.TransientModel):
    _name = 'account.move.import.line'

    name_company = fields.Char()
    selected = fields.Boolean(default=False)
    id_account_move = fields.Integer()
    line_id = fields.Many2one('account.move.import', 'line_ids')
