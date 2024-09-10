from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SalePromotion(models.Model):
    _name = 'sale.promotion'
    _description = "Sale Promotion"

    name = fields.Char('Comment', required=True)
    date_start = fields.Datetime('Starting Date', required=True)
    date_end = fields.Datetime('End Date', required=True)
    quantity = fields.Float('Qty')
    promotion = fields.Selection([
        ('promotion', 'Promotion'),
        ('challenge', 'Challenge'),
        ('push', 'Push'),
        ('novelty', 'Novelty'),
        ('terrain', 'Terrain'),
        ('various', 'Various')
    ], string='Type', default='promotion')
    qty_executed = fields.Integer('Qty Ok', compute='_update_info')
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('sale_ok', '=', True)])
    discount = fields.Float('Rem %')

    def _update_info(self):
        for promotion in self:
            sale_order_line_obj = self.env['sale.order.line']
            lines = sale_order_line_obj.search([
                ('state', 'not in', ['cancel']),
                ('product_id', '=', promotion.product_id.id),
                ('order_id.commitment_date', '>=', promotion.date_start),
                ('order_id.commitment_date', '<=', promotion.date_end)
            ])
            promotion.qty_executed = sum(line.product_uom_qty for line in lines)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start > rec.date_end:
                raise ValidationError("La date de début doit être antérieure à la date de fin.")