from odoo import models, fields, tools

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    cost_price = fields.Float(string="Cost Price", readonly=True)
    margin = fields.Float(string='Marge total', readonly=True)
    weight = fields.Float(string="Weight", readonly=True)
    user2_id = fields.Many2one('res.users',  readonly=True)

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + """
        ,
        line.cost_price as cost_price, 
        line.margin as margin,
        line.weight as weight,
        line.weight as weight,
        line.user2_id as user2_id
        
        """


