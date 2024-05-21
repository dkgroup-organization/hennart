# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import fields, models, tools, api, _


class ReportStockQuant2(models.Model):
    _name = 'report.stock.quant2'
    _auto = False
    _description = 'Stock by warehouse'

    name = fields.Char('name', compute='compute_color')

    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    categ_id = fields.Many2one('product.category', string="Category", readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)

    bg_color = fields.Char('color', compute='compute_color')

    def compute_color(self):
        """ return move_ids of this stock value"""
        for stock_quantity in self:
            bg_color = "white"
            name = stock_quantity.product_id.name
            if stock_quantity.product_qty < 0.0:
                bg_color = "red"
            stock_quantity.bg_color = bg_color
            stock_quantity.name = "%s" % (stock_quantity.product_id.name)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_quant2')

        query = """
CREATE or REPLACE VIEW report_stock_quant2 AS (

    SELECT
        min(q.id) as id,
        q.product_id,
        min(pt.categ_id) as categ_id,
        sum(q.quantity) as product_qty,
        q.lot_id,
        l.company_id as company_id,
        l.warehouse_id as warehouse_id
 
    FROM
        stock_quant q
        
    LEFT JOIN stock_location l on (l.id=q.location_id)
    LEFT JOIN product_product pp on pp.id=q.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    
    WHERE
        (l.usage = 'internal' AND l.warehouse_id IS NOT NULL) OR l.usage = 'transit'
        
    GROUP BY product_id, lot_id, l.company_id, l.warehouse_id
);
"""

        self.env.cr.execute(query)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        for i in range(len(domain)):
            if domain[i][0] == 'product_tmpl_id' and domain[i][1] in ('=', 'in'):
                tmpl = self.env['product.template'].browse(domain[i][2])
                # Avoid the subquery done for the related, the postgresql will plan better with the SQL view
                # and then improve a lot the performance for the forecasted report of the product template.
                domain[i] = ('product_id', 'in', tmpl.with_context(active_test=False).product_variant_ids.ids)
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
