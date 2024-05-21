# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import fields, models, tools, api, _


class ReportStockWeekPrevision(models.Model):
    _name = 'report.stock.weekprevision'
    _auto = False
    _description = 'Stock Quantity Report by Week'

    name = fields.Char('name', compute='compute_color')
    date = fields.Date(string='Date', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    categ_id = fields.Many2one('product.category', string="Category", readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)

    company_id = fields.Many2one('res.company', readonly=True)
    json_moves = fields.Char('Json move', readonly=True)
    move_ids = fields.Many2many('stock.move', compute='compute_moves_ids')
    bg_color = fields.Char('color', compute='compute_color')

    def compute_moves_ids(self):
        """ return move_ids of this stock value"""
        for stock_quantity in self:
            move_ids = self.env['stock.move']
            for item_id in stock_quantity.json_moves:
                item_id = item_id and int(item_id) or 0
                if item_id and item_id > 0:
                    move_ids |= self.env['stock.move'].browse(item_id)
            # move_ids.sorted(key=lambda m: m.date, reverse=True)
            stock_quantity.move_ids = move_ids

    def compute_color(self):
        """ return move_ids of this stock value"""
        for stock_quantity in self:
            bg_color = "white"
            name = stock_quantity.product_id.name
            if stock_quantity.product_qty < 0.0:
                bg_color = "red"
            stock_quantity.bg_color = bg_color
            stock_quantity.name = "%s: %s" % (stock_quantity.date, stock_quantity.product_id.name)

    def open_product_replenish(self):
        """ Open the wizard to replenish the forecasted product"""
        add_context = {
            'active_model': self._name,
            'active_ids': self.ids
        }
        return {
            'name': _('Replenish'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.route.multireplenish',
            'target': 'new',
            'context': add_context,
        }

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_weekprevision')

        # the construction of the id has some limitation to know due to the max value of integer: 2 147 483 648
        #only 200 warehouses_id, only 99 999 product_id, only 1 years forecast
        #COALESCE(warehouse_id, 0)::int * 10000000 + product_id * 100 + to_char(date, 'WW')::int AS id,
        # With this computing there is no double id

        futur_horizon = '1 month'
        past_horizon = '1 month'

        query = """
CREATE or REPLACE VIEW report_stock_weekprevision AS (
SELECT
    COALESCE(warehouse_id, 0)::int * 10000000 + COALESCE(product_id, 0)::int * 100 + to_char(date, 'WW')::int AS id,
    json_agg(json_moves) AS json_moves,
    product_id,
    max(categ_id) as categ_id,
    date,
    sum(product_qty) as product_qty,
    company_id,
    warehouse_id
    
     
FROM (   
    
    SELECT
        -q.id as json_moves,
        q.product_id,
        pt.categ_id,
        date.*::date,
        q.quantity as product_qty,
        q.company_id,
        l.warehouse_id as warehouse_id
 
    FROM
        GENERATE_SERIES(
        date_trunc('week',(now() at time zone 'utc')::date),
        date_trunc('week',(now() at time zone 'utc')::date + interval 'futur_horizon')::date, '1 week'::interval) date,
        stock_quant q
        
    LEFT JOIN stock_location l on (l.id=q.location_id)
    LEFT JOIN product_product pp on pp.id=q.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    
    WHERE
        (l.usage = 'internal' AND l.warehouse_id IS NOT NULL) OR l.usage = 'transit'
    
    
UNION ALL 

    SELECT
        m.id as json_moves,
        m.product_id,
        pt.categ_id,
        GENERATE_SERIES(date_trunc('week',
            CASE
                WHEN m.date < now() THEN (now() at time zone 'utc')::date  
                ELSE (m.date + interval '4 hours')::date
            END),
            
            date_trunc('week', (now() at time zone 'utc')::date + interval 'futur_horizon'),
            '1 week'::interval)::date date,
                    
        -m.product_qty AS product_qty,
        m.company_id,           
        m.whs_id AS warehouse_id
    FROM
        stock_move m

    LEFT JOIN product_template pt on pt.id = m.product_tmpl_id
    
    WHERE
        m.wh_filter IS TRUE AND
        m.whs_id IS NOT NULL AND       
        m.date > (now() at time zone 'utc')::date - interval 'past_horizon'
        
        
UNION ALL
   
   SELECT
        m.id as json_moves,
        m.product_id,
        pt.categ_id,
        GENERATE_SERIES(date_trunc('week',
            CASE
                WHEN m.date < now() THEN (now() at time zone 'utc')::date  
                ELSE (m.date + interval '4 hours')::date
            END),
            
            date_trunc('week', (now() at time zone 'utc')::date + interval 'futur_horizon'),
            '1 week'::interval)::date date,
                    
        m.product_qty AS product_qty,
        m.company_id,           
        m.whd_id AS warehouse_id
    FROM
        stock_move m

    LEFT JOIN product_template pt on pt.id = m.product_tmpl_id
    
    WHERE
        m.wh_filter IS TRUE AND
        m.whd_id IS NOT NULL AND       
        m.date > (now() at time zone 'utc')::date - interval 'past_horizon'
        
) AS prevision_qty

        
GROUP BY product_id, date, company_id, warehouse_id
);

"""

        query = query.replace('past_horizon', past_horizon).replace('futur_horizon', futur_horizon)
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
