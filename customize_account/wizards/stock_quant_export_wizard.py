from odoo import models, fields, api
import base64
import io
import xlsxwriter


class StockQuantExportWizard(models.TransientModel):
    _name = 'stock.quant.export.wizard'
    _description = 'Wizard for Stock Quant Export'

    date = fields.Date('Date')

    def action_export(self):
        quant_export = self.env['stock.quant.export'].create({'date': self.date})
        date = self.date.strftime('%Y-%m-%d 04:00:00')
        date_now = fields.Date.today().strftime('%Y-%m-%d 04:00:00')

        sql = f""" 
        SELECT squ.product_id, squ.lot_id, sum(squ.quantity)
        FROM (
        
        SELECT sq.product_id, sq.lot_id, sq.quantity
        FROM stock_quant sq, stock_location sl
        WHERE sq.location_id = sl.id and sl.usage = 'internal'
        
        UNION
        
        SELECT sm.product_id, sml.lot_id, sml.qty_done as quantity
        FROM stock_move sm, stock_move_line sml
        WHERE sml.move_id = sm.id and sm.export_filter = 'out'
        AND sm.date > '{date}' AND sm.date < '{date_now}'
        
        UNION
        
        SELECT sm.product_id, sml.lot_id, - sml.qty_done as quantity
        FROM stock_move sm, stock_move_line sml
        WHERE sml.move_id = sm.id and sm.export_filter = 'in'
        AND sm.date > '{date}' AND sm.date < '{date_now}'
        
        ) AS squ, product_product pp
        
        WHERE squ.product_id = pp.id
        
        GROUP BY squ.product_id, squ.lot_id, pp.default_code
        HAVING sum(squ.quantity) > 0.0
        ORDER BY pp.default_code
        
        """
        self.env.cr.execute(sql)
        result_sql = self.env.cr.fetchall()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet(self.date.strftime('stock_%Y_%m_%d'))
        # Création du titre
        worksheet.write(0, 0, 'code')
        worksheet.write(0, 1, 'produit')
        worksheet.write(0, 2, 'lot')
        worksheet.write(0, 3, 'transformation')
        worksheet.write(0, 4, 'coupe')
        worksheet.write(0, 5, 'affinage')
        worksheet.write(0, 6, 'achat 6 mois')
        worksheet.write(0, 7, 'achat actuelle')
        worksheet.write(0, 8, 'prix atelier')
        worksheet.write(0, 9, 'poids')
        worksheet.write(0, 10, 'Quantité')
        worksheet.write(0, 11, 'prix unité')
        worksheet.write(0, 12, 'prix poids')
        worksheet.write(0, 13, 'unité vente')
        worksheet.write(0, 14, 'unité achat')
        worksheet.write(0, 15, 'fournisseur')
        worksheet.write(0, 16, 'date entrée')
        worksheet.write(0, 17, 'Valeur')

        row = 1
        for line in result_sql:
            product = self.env['product.product'].browse(line[0])
            lot = self.env['stock.lot'].browse(line[1])
            quantity = float(line[2])

            worksheet.write(row, 0, product.default_code)
            worksheet.write(row, 1, product.name)
            worksheet.write(row, 2, lot.ref)
            worksheet.write(row, 3, product.transformation_cost)
            worksheet.write(row, 4, product.cutting_cost)
            worksheet.write(row, 5, product.refinement_cost)
            worksheet.write(row, 6, product.average_cost_price)
            worksheet.write(row, 7, product.current_cost_price)
            worksheet.write(row, 8, product.workshop_cost_price)
            worksheet.write(row, 9, quantity * lot.unit_weight)
            worksheet.write(row, 10, quantity)
            worksheet.write(row, 11, lot.unit_price)
            worksheet.write(row, 12, lot.kg_price)
            worksheet.write(row, 13, lot.uos_id.name)
            worksheet.write(row, 14, lot.partner_supplier_uos_id.name)
            worksheet.write(row, 15, lot.partner_supplier_id.name)
            worksheet.write(row, 16, lot.partner_supplier_date)
            worksheet.write(row, 17, quantity * lot.unit_price)

            row += 1

        # Finaliser et enregistrer le fichier
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read()).decode('utf-8')
        file_name = self.date.strftime('stock_%Y_%m_%d.xlsx')

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

