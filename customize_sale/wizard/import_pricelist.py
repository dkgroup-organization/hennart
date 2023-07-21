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
    _name = 'import.pricelist'
    _description = "Import the sale price list"

    file = fields.Binary('Import File')
    name = fields.Char('Name')

    example_id = fields.Many2one('ir.attachment', 'Example file')
    file_name = fields.Char('File name')
    # message = fields.Html("Message")
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Price List',
    )


    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)

        binary_content = base64.b64encode(self.from_data())
        binary_name = "import_list_de_prix_0.xlsx"
        #creation attachment file or update
        attachment_id = self.env['ir.attachment'].search([('type','=','binary'),('name','=',binary_name)],limit=1)
        if attachment_id:
            attachment_id.write({'datas': binary_content})
        else:
            attachment_vals = {'type': 'binary', 'name': binary_name, 'datas': binary_content}
            attachment_id = self.env['ir.attachment'].create(attachment_vals)
        rec.update({
            'pricelist_id': self.pricelist_id,
            'example_id' : attachment_id.id,
        })
        return rec

    def action_export_file(self):
        self.ensure_one()

        if self.env.context.get('pricelist_id'):
            binary_name = "import_list_de_prix_{}.xlsx".format(self.env.context.get('pricelist_id'))

            # creation attachment file or update
            condition = [
                ('res_model', '=', 'product.pricelist'),
                ('res_id', '=', self.env.context.get('pricelist_id')),
                ('name', '=', binary_name)
            ]
            attachment_ids = self.env['ir.attachment'].search(condition)

            if attachment_ids:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/%s' % attachment_ids[0].id
                }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s' % self.example_id.id
            }

    def action_valide(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please select a file to import."))

        book = xlrd.open_workbook(file_contents=base64.b64decode(self.file))
        sheet = book.sheet_by_index(0)

        product_items = []

        pricelist_items = self.pricelist_id.item_ids
        product_ids = pricelist_items.mapped('product_id')

        for row in range(1, sheet.nrows):
            product_code = sheet.cell_value(row, 0)
            list_price = sheet.cell_value(row, 1)
            # start_date_value = sheet.cell_value(row, 2)
            # end_date_value = sheet.cell_value(row, 3)

            if product_code and list_price:
                product = product_ids.filtered(lambda p: p.default_code == product_code)[:1]
                if product:
                    # start_date = xlrd.xldate_as_datetime(start_date_value, book.datemode) if start_date_value else None
                    # end_date = xlrd.xldate_as_datetime(end_date_value, book.datemode) if end_date_value else None

                    item_values = {
                        'pricelist_id': self.pricelist_id.id,
                        'product_id': product.id,
                        'fixed_price': list_price,
                        'compute_price': 'fixed',
                        'applied_on': '0_product_variant',
                        # 'date_start': start_date.strftime('%Y-%m-%d 00:00:00') if start_date else False,
                        # 'date_end': end_date.strftime('%Y-%m-%d 00:00:00') if end_date else False,
                    }
                    product_items.append(item_values)

        if product_items:
            existing_items = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', self.pricelist_id.id),
                ('product_id', 'in', product_ids.ids)
            ])
            existing_items.unlink()
            self.env['product.pricelist.item'].create(product_items)

        return True

    def from_data(self):
        # fields = ['product_code', 'product_name', 'list_price', 'start_date', 'end_date']
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

        with ExportXlsxWriter2(fields, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        """ Update content of exemple file"""

        binary_content = base64.b64encode(self.from_data())
        binary_name = "import_list_de_prix_{}.xlsx".format(self.pricelist_id.id or 0)

        # creation attachment file or update
        attachment_ids = self.env['ir.attachment'].search([
            ('res_model', '=', 'product.pricelist'),
            ('res_id', '=', self.pricelist_id.id or 0),
            ('name', '=', binary_name)
        ])

        if attachment_ids:
            attachment = attachment_ids[0]
            attachment.write({'datas': binary_content})
        else:
            attachment_vals = {
                'type': 'binary', 'name': binary_name, 'datas': binary_content,
                'res_model': 'product.pricelist', 'res_id': self.pricelist_id.id or 0}
            attachment = self.env['ir.attachment'].create(attachment_vals)
        print('-------------', attachment)
        self.example_id = attachment


class ExportXlsxWriter2(ExportXlsxWriter):
    """ change column width
    """

    def write_header(self):
        # Write main header
        for i, fieldname in enumerate(self.field_names):
            self.write(0, i, fieldname, self.header_style)
        self.worksheet.set_column(0, 1, 15)  # around 220 pixels
        self.worksheet.set_column(2, 2, 60)
        self.worksheet.set_column(3, i, 4)
