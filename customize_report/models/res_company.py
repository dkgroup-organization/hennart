from odoo import fields, models, api, _

class ResCompanyInherits(models.Model):
    _inherit = 'res.company'

    
    invoice_text = fields.Text(
        string='Invoice Text',
    )
    