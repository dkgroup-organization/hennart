from odoo import fields, models, api



class AccountJournal(models.Model):
    _inherit = "account.journal"

    country_ids = fields.Many2many('res.country', string="Country")



