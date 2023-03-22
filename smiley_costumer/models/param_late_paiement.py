
from odoo import api,fields,models,_


class param_late_paiement(models.Model):
    _name = "param.late.paiement"
    _description = "param paiement"

    limit1 = fields.Integer('Limit 1')
    limit2 = fields.Integer('Limit 2')
    partner_id = fields.Many2one('res.partner', 'Customer')
    level = fields.Selection([('green', 'Green'), ('orange', 'Orange'), ('red', 'Red')], 'Level')
