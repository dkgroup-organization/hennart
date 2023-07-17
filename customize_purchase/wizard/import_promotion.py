# -*- coding: utf-8 -*-
from odoo import fields, models, api,_
from odoo.exceptions import UserError, ValidationError
import base64
import time
import logging
import io,csv
import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.web.controllers.export import ExportXlsxWriter
from odoo.tools import lazy_property, osutil, pycompat
from odoo.http import  content_disposition, request



FORMAT_DATE = [('ddmmyy', 'ddmmyy'),('dd/mm/yyyy', 'dd/mm/yyyy'), ('yyyy-mm-dd', 'yyyy-mm-dd'), ('yyyymmdd', 'yyyymmdd'), ('mm/dd/yyyy', 'mm/dd/yyyy')]
MIN_COLUMN = 2
ANNEE = int(time.strftime('%Y'))
FORMAT_ANNEE = [(str(ANNEE), str(ANNEE)), (str(ANNEE+1) , str(ANNEE+1))]

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


class ImportPromotion(models.TransientModel):
    _name = 'import.promotion'
    _description = "Import promotion"

    file = fields.Binary('Import File')
    name = fields.Char('Name')
    date = fields.Selection(FORMAT_DATE, string="Date")
    year = fields.Selection(FORMAT_ANNEE, string='Annee')
    example_id = fields.Many2one('ir.attachment','example file')
    file_name = fields.Char('File name')
    message = fields.Html("Message")

    def week_info(self,year,week):
        startdate = datetime.date(int(year),1,1)+relativedelta(weeks=+week)
        enddate = startdate + datetime.timedelta(days=6)
        data = {'date_start':startdate.strftime('%Y-%m-%d 00:00:00'),'date_end':enddate.strftime('%Y-%m-%d 00:00:00')}
        return data

    def action_export_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/%s' % self.example_id.id
        }

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        year = ANNEE + 1
        #binary_content = base64.b64encode(content.encode())
        binary_content = base64.b64encode(self.from_data())
        binary_name = "import_promo_fournisseur_%s.xlsx" % (year)
        #creation attachment file or update
        attachment_id = self.env['ir.attachment'].search([('type','=','binary'),('name','=',binary_name)],limit=1)
        if attachment_id:
            attachment_id.write({'datas': binary_content})
        else:
            attachment_vals = {'type': 'binary', 'name': binary_name, 'datas': binary_content}
            attachment_id = self.env['ir.attachment'].create(attachment_vals)
        rec.update({
            'year': str(year),
            'example_id' : attachment_id.id,
        })
        return rec

    def action_valide(self):
        self.ensure_one()
        if(not self.file):

            self.message ='<div class="alert alert-danger" role="alert"> Veuillez saisir le fichier xlsx </div>'
            return {
                'name': _('Import promotion'),
                'view_mode': 'form',
                'view_id': False,
                'res_model': self._name,
                'domain': [],
                'context': dict(self._context, active_ids=self.ids),
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': self.id,
            }
            #return
        elif(not self.year):
            self.message = '<div class="alert alert-danger" role="alert"> Veuillez sélectionner l\'année </div>'
            return {
                'name': _('Import promotion'),
                'view_mode': 'form',
                'view_id': False,
                'res_model': self._name,
                'domain': [],
                'context': dict(self._context, active_ids=self.ids),
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': self.id,
            }

        elif(self.file):
            self.message = False
            book = xlrd.open_workbook(file_contents=base64.b64decode(self.file) or b'')
            sheets = book.sheet_names()
            sheet = sheets[0]
            sheet = book.sheet_by_name(sheet)
            rows = []
            week_start = 3
            week_end = 54
            # emulate Sheet.get_rows for pre-0.9.4
            for row in map(sheet.row, range(1, sheet.nrows)):
                values = []
                if (not row[0].value) or (not row[1].value) or str(row[0].value) == 'False' or str(
                        row[1].value) == 'False':
                    continue
                code_product = str(row[1].value).strip()
                code_product = code_product.split('.')[0]
                code_supplier = str(row[0].value).strip()
                if len(code_product) == 4:
                    code_product = '0' + code_product
                if code_product[-1] in ['A', 'B', 'C', 'D', 'E', 'F', 'G',
                                        'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'] and len(code_product) == 5:
                    code_product = '0' + code_product

                product_id = self.env['product.product'].search([('default_code', '=', code_product)], limit=1)
                if not product_id:
                    raise ValidationError(_('Unknown product code %s' % (code_product)))
                # partner
                supplier_id = self.env['res.partner'].search([('ref', '=', code_supplier)], limit=1)
                if not supplier_id:
                    raise ValidationError(_('Unknown vendor code %s' % (code_supplier)))

                for week_number in range(week_start, week_end + 1):
                    if row[week_number].value:
                        try:
                            promo_value = float(row[week_number].value)
                        except:
                            raise ValidationError(
                                _('Incorrect value: %s\n for %s %s' % (
                                    row[week_number], code_supplier,
                                    code_product)))

                        week_info = self.week_info(self.year, (int(week_number) - 3))
                        if not week_info:
                            raise ValidationError(_('Wrong week: week %s\n' % (week_number)))

                        vals_promo = {'supplier_id': supplier_id.id, 'product_id': product_id.id}
                        condition = [('supplier_id', '=', supplier_id.id), ('product_id', '=', product_id.id)]

                        date_start = week_info['date_start']
                        date_end = week_info['date_end']

                        vals_promo['date_start'] = date_start
                        vals_promo['date_end'] = date_end
                        vals_promo['discount'] = promo_value

                        # chevauchement
                        condition1 = condition + [('date_start', '<', date_start), ('date_end', '>=', date_start)]
                        condition2 = condition + [('date_start', '<=', date_end), ('date_end', '>', date_end)]
                        condition3 = condition + [('date_start', '>', date_start), ('date_end', '<', date_end)]

                        for check_condition in [condition1, condition2, condition3]:
                            promo_ids = self.env['purchase.promotion'].search(check_condition)
                            if promo_ids:
                                raise ValidationError(
                                    _('Date overlap: date %s au %s\n for %s %s' % (date_start, date_end,
                                                                                   code_supplier,
                                                                                   code_product)))

                        # Create or rewrite
                        condition_final = condition + [('date_start', '=', date_start), ('date_end', '=', date_end)]
                        promo_ids = self.env['purchase.promotion'].search(condition_final)
                        if promo_ids:
                            promo_ids.write({'discount': promo_value})
                        else:
                            self.env['purchase.promotion'].create(vals_promo)

        #return True


    def from_data(self,year=False):
        fields = ['CODE_FOURNISSEUR','CODE_PRODUIT','DESCRIPTION(facultatif)']
        for week in range(1, 54):
            fields.append(str(week))
        if(not year):
            year = ANNEE + 1
        date_start_p = "%s-01-01 00:00:00" % (year-1)
        date_end_p = "%s-12-31 23:59:59" % (year)
        price_purchase = self.env['product.supplierinfo'].search([])
        result = {}
        partner = {}
        products = []
        for promotion in price_purchase:
            if promotion.partner_id.ref not in list(result.keys()):
                result[promotion.partner_id.ref] = []
                partner[promotion.partner_id.ref] = promotion.partner_id.name
            if promotion.product_tmpl_id.default_code not in products:
                products.append((promotion.product_tmpl_id.default_code))
                data = {'default_code':promotion.product_tmpl_id.default_code,'name':promotion.product_tmpl_id.name,'id':promotion.product_tmpl_id.id,'partner_id':promotion.partner_id.id,'partner_name':promotion.partner_id.name}
                result[promotion.partner_id.ref].append(data)
        rows=[]
        list_partner = list(result.keys())
        for ref_partner in list_partner:
            list_product = result[ref_partner]
            for code_product in list_product:
                condition = [('supplier_id', '=', code_product['partner_id']), ('product_id', '=', code_product['id']),('date_start', '!=', False),('date_start', '>=', date_start_p),('date_end', '!=', False), ('date_end', '<=', date_end_p)]
                promotion_ids = self.env['purchase.promotion'].search(condition)
                data= [ref_partner if ref_partner else '',code_product['default_code'] if code_product['default_code'] else '', '%s [%s]' %(code_product['name'],code_product['partner_name'])]
                for i in range(2, 55):
                    data.append('')
                if(promotion_ids):
                    for promo in promotion_ids:
                        date_week = promo.date_start.date()
                        week = date_week.isocalendar()[1]
                        data[week +2] =  promo.discount if promo.discount else ''
                rows.append(data)
        with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            xlsx_writer.worksheet.set_column(0, 1, 15)
            xlsx_writer.worksheet.set_column(2, 2, 60)
            xlsx_writer.worksheet.set_column(3, 56, 4)
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(row_index + 1, cell_index, str(cell_value))

        return xlsx_writer.value