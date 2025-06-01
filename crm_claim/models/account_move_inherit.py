# Copyright 2015-2017 Odoo S.A.
# Copyright 2017 Tecnativa - Vicent Cubells
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import models, fields, api, _



class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    has_claim = fields.Boolean(string="Has Claim", compute='_compute_has_claim')

    @api.depends('partner_id')
    def _compute_has_claim(self):
        for move in self:
            domain = [
                ('invoice', '=', move.id),
                ('partner_id', '=', move.partner_id.id),
            ]
            claim_exists = self.env['crm.claim'].search_count(domain) > 0
            move.has_claim = claim_exists

    def action_view_related_claims(self):
        self.ensure_one()
        return {
            'name': _('Réclamations liées'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.claim',
            'view_mode': 'tree,form',
            'target': 'new',
             'views': [
                (self.env.ref('crm_claim.view_claim_tree_popup').id, 'tree'),
                (False, 'form')
            ],
            'domain': [
                ('invoice', '=', self.id),
                ('partner_id', '=', self.partner_id.id),
            ],
            'context': {
                'default_invoice': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }
