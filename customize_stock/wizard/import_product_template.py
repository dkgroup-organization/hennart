# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import time
import logging
import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.web.controllers.export import ExportXlsxWriter

FORMAT_DATE = [('ddmmyy', 'ddmmyy'), ('dd/mm/yyyy', 'dd/mm/yyyy'), ('yyyy-mm-dd', 'yyyy-mm-dd'),
               ('yyyymmdd', 'yyyymmdd'), ('mm/dd/yyyy', 'mm/dd/yyyy')]
MIN_COLUMN = 2
ANNEE = int(time.strftime('%Y'))
FORMAT_ANNEE = [(str(ANNEE), str(ANNEE)), (str(ANNEE + 1), str(ANNEE + 1))]

_logger = logging.getLogger(__name__)
try:
    import xlrd

    try:
        from xlrd import xlsx
    except ImportError:
        _logger.info("xlsx None")
        xlsx = None
except ImportError:
    _logger.info("xlrd None")
    xlrd = xlsx = None


class ImportPriceList(models.TransientModel):
    _name = 'import.product.template'
    _description = "Import product template"

    file = fields.Binary('Import File')
    name = fields.Char('Name')

    file_name = fields.Char('File name')

    def action_valide(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please select a file to import."))
        if not self.pricelist_id:
            raise UserError(_("Please select a price list to import."))

        product_ids = self.env['product.product'].search([('company_id', '=', False)])
        product_ids.write({'company_id': self.env.user.company_id.id})

        book = xlrd.open_workbook(file_contents=base64.b64decode(self.file))
        sheet = book.sheet_by_index(0)
        header = {}
        for i_col in range(sheet.ncols):
            header_name = sheet.cell_value(0, i_col)
            header[header_name] = i_col

        for row in range(1, sheet.nrows):

            product_code = sheet.cell_value(row, header.get('product_code'))
            list_price = sheet.cell_value(row, header.get('list_price'))

            if product_code and list_price:
                product = self.env['product.product'].search([('default_code', '=', product_code)])
                if not product:
                    raise UserError(_("This product code is unknown: {}".format(product_code)))

                condition = [('product_id', '=', product.id), ('pricelist_id', '=', self.pricelist_id.id)]
                item_ids = self.pricelist_id.item_ids.search(condition)

                item_values = {
                        'pricelist_id': self.pricelist_id.id,
                        'product_id': product.id,
                        'fixed_price': list_price,
                        'compute_price': 'fixed',
                        'applied_on': '0_product_variant',
                    }

                if self.pricelist_id.id == 1:
                    product.list_price = list_price
                elif item_ids:
                    item_ids.write(item_values)
                else:
                    item_ids.create(item_values)
        return True

    def from_data(self):
        fields = ['product_code', 'product_name', 'list_price']

        rows = []

        if self.pricelist_id:
            for item in self.pricelist_id.item_ids:
                if item.compute_price == "fixed" and item.product_id.default_code:
                    data = [str(item.product_id.default_code), str(item.product_id.name), float(item.fixed_price)]
                    rows.append(data)
        else:
            product_prices = self.env['product.product'].search([('default_code', '!=', False)])
            for product in product_prices:
                data = [str(product.default_code), str(product.name), float(product.list_price)]
                rows.append(data)

        with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value

