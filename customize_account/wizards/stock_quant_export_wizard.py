from odoo import models, fields, api

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

        data = []
        for line in result_sql:
            product = self.env['product.product'].browse(line[0])
            lot = self.env['stock.lot'].browse(line[1])
            quantity = float(line[2])
            print(product.default_code, product.name, lot.ref, quantity)



        # return self.env['stock.quant.export'].create({}).export_stock_quant()
