
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
    temp_old_barcode = fields.Char(string='Temp Old Barcode 1')
    temp2_old_barcode = fields.Char(string='Temp Old Barcode 2')
    barcode = fields.Char(string='Barcode', compute="get_barcode", store=True)
    barcode_ext = fields.Char(string='Barcode (external)', compute="get_barcode", store=True)

    def put_ref(self):
        """ Write ref on lot"""
        for lot in self:
            if not lot.ref:
                # Search doubloon
                lot_ids = self.search([('name', '=', lot.name)])
                suffix = '-' + str(len(lot_ids)).zfill(2)
                lot.ref = lot.name + suffix

    def get_barcode(self):
        """ define the barcode of lot
        the barcode is composite with:
        5 char: product code
        7 char: stock.lot.id
        1 char: product code type
        6 char: expiration date
        6 char: weight
        """
        for lot in self:
            # format product code with length of 6
            if lot.product_id and len(lot.product_id.default_code) == 5:
                product_code = lot.product_id.default_code + 'X'
            elif lot.product_id and len(lot.product_id.default_code) == 6:
                product_code = lot.product_id.default_code or ''
            else:
                product_code = '00000X'

            label_dlc = lot.expiration_date or lot.use_date or lot.date
            label_dlc_new = label_dlc.strftime("%d%m%y")
            label_dlc_old = label_dlc.strftime("%d%m%Y")

            lot.barcode = product_code[:5] + str(lot.id).zfill(7) + product_code[5] + label_dlc_new + '000000'

            if lot.temp_old_barcode:
                lot.barcode_ext = lot.temp_old_barcode
            else:
                lot.barcode_ext = product_code[:5] + lot.name[:6] + product_code[5] + label_dlc_old + '000000'