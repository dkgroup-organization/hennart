
from odoo import api, fields, models, _


class Stock_lot(models.Model):
    _inherit = 'stock.lot'

    company_id = fields.Many2one('res.company', 'Company', 
                                 required=True, 
                                 store=True, 
                                 index=True, 
                                #  added default to not violates not-null constraint at db_synchro
                                 default=lambda self: self.env.company)

    date = fields.Date(string='Date de création')
    life_date = fields.Date(string='Date limite de consommation')
    temp_old_barcode = fields.Char(string='Temp Old Barcode')