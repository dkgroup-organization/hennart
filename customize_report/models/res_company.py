from odoo import fields, models, api, _

class ResCompanyInherits(models.Model):
    _inherit = 'res.company'

    
    invoice_header_text = fields.Text(
        string='Invoice Header Text',
    )

    invoice_footer_text = fields.Text(
        string='Invoice Footer Text',
        translate=True,
    )
    