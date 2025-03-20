from odoo import models, fields, api
import base64
import io
import xlsxwriter


class StockQuantExport(models.TransientModel):
    _name = 'stock.quant.export'
    _description = 'Export Stock Quantities'

    file = fields.Binary('File', readonly=True)
    filename = fields.Char('Filename')
    date = fields.Date('Date')

    def export_stock_quant(self):
        # Créez un flux pour stocker le fichier Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Stock Quant')

        # Création du titre
        worksheet.write(0, 0, 'Product')
        worksheet.write(0, 1, 'Location')
        worksheet.write(0, 2, 'Quantity')

        # Rechercher les stock.quant où l'emplacement a un usage interne
        stock_quants = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal')
        ])

        row = 1
        for quant in stock_quants:
            worksheet.write(row, 0, quant.product_id.name)
            worksheet.write(row, 1, quant.location_id.name)
            worksheet.write(row, 2, quant.quantity)
            row += 1

        # Finaliser et enregistrer le fichier
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        self.write({
            'file': file_data,
            'filename': 'stock_quant_export.xlsx'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.export',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'res_id': self.id,
        }
