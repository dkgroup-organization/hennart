from odoo import fields, models, api

class AccountMove(models.Model):
    _inherit = "account.move"

    week_number = fields.Integer('Week number', store=True, compute='compute_week_number')

    @api.depends('invoice_date')
    def compute_week_number(self):
        """ compute invoice date week number """
        cadence = self.env['res.partner.cadence']

        for move in self:
            move.week_number = cadence.get_week_number(date=move.invoice_date)
