# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    export_id = fields.Many2one('account.export.history', copy=False, string="Export")

    def button_unlink_export(self):
        "unlink previous link to export history"
        for move in self:
            move.export_id = False

    def check_tiers_account(self):
        """ Check if all partner have a tiers account before export"""
        # compte tiers
        partner_ko_ids = self.env['res.partner']
        for move in self:
            for line in move.line_ids:
                if line.compte_tiers and line.compte_tiers == '?':
                    partner_ko_ids |= line.move_id.partner_id
        if partner_ko_ids:
            message = _("This list of partner have no tiers account. Please, complete the configuration:\n")
            for partner in partner_ko_ids:
                message += "\n%s" % (partner.name)
            raise ValidationError(message)

    def check_account(self):
        """ Check if all partner have a tiers account before export"""
        # account tiers
        account_ko_ids = self.env['account.account']
        for move in self:
            for line in move.line_ids:
                if not line.account_id.export_code:
                    account_ko_ids |= line.account_id
        if account_ko_ids:
            message = _("This list of account do not have export code. Please, complete the configuration:\n")
            for account in account_ko_ids:
                message += "\n%s : %s" % (account.code, account.name)
            raise ValidationError(message)
