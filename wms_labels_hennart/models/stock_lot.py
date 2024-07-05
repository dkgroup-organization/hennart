
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import datetime
import time

class StockLot(models.Model):
    _inherit = 'stock.lot'

    def get_weight(self):
        """ Return value to print on label """
        self.ensure_one()
        weight = self.env.context.get('weight')
        if weight:
            res = f"{weight:.3f} Kg"
        else:
            res = ''
        return res

    def get_label_weight(self):
        """ Return value to print on label """
        self.ensure_one()
        weight = self.env.context.get('weight')
        if weight:
            res = _("Net Weight:")
        else:
            res = ''
        return res

    def get_label_barcode(self):
        """ Add weight on label barcode """
        self.ensure_one()
        weight = self.env.context.get('weight')
        barcode = self.barcode
        if weight and weight < 100.0:
            weight_label = f"{weight:.3f}".zfill(6)
            barcode = barcode[:-6] + weight_label
        return barcode
