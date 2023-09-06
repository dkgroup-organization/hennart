# Copyright 2004-2016 Odoo SA (<http://www.odoo.com>)
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class ResPartner(models.Model):
    """Added the details of phonecall in the partner."""

    _inherit = "res.partner"

    phonecall_ids = fields.One2many(
        comodel_name="crm.phonecall", inverse_name="partner_id", string="Phonecalls"
    )
    phonecall_count = fields.Integer(compute="_compute_phonecall_count")
    user2_id = fields.Many2one('res.users', 'Manager',
                               help='The internal user that is in charge of communicating with this contact if any.')
    appointment_ids = fields.One2many('partner.crm.appointment', 'partner_id', 'Call apppointement')
    appointment_delivery_ids = fields.One2many('partner.delivery.appointment', 'partner_id', 'Delivery apppointement')

    def _compute_phonecall_count(self):
        """Calculate number of phonecalls."""
        for partner in self:
            partner.phonecall_count = self.env["crm.phonecall"].search_count(
                [("partner_id", "=", partner.id), ('state', 'in', ['open', 'pending'])]
            )

