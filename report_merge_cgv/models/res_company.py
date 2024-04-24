from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'
    cgv_binary = fields.Binary('Conditions générales de vente')