# Copyright 2015-2017 Odoo S.A.
# Copyright 2017 Tecnativa - Vicent Cubells
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models, _


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    def add_claim(self):
        self.ensure_one()
        context = dict(self.env.context)
        context['default_invoice'] = self.id
        context['default_partner_id'] = self.partner_id.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.claim",
            "view_mode": 'form',
            "context": context,
            "target": "new",
            "name": _("Add Claim"),
        }
