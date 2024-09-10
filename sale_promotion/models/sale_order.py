from odoo import models, api, Command

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('commitment_date')
    def _onchange_commitment_date(self):
        if self.commitment_date:
            promotions = self.env['sale.promotion'].search([
                ('date_start', '<=', self.commitment_date),
                ('date_end', '>=', self.commitment_date)
            ])

            new_lines = []
            for promo in promotions:
                if promo.qty_executed >= promo.quantity:
                    continue
                line = self.order_line.filtered(lambda l: l.product_id == promo.product_id)

                if line:
                    line.discount = promo.discount
                else:
                    new_lines.append(Command.create({
                        'product_id': promo.product_id.id,
                        'product_uom_qty': 0,
                        'discount': promo.discount,
                        'price_unit': promo.product_id.list_price,
                    }))

            if new_lines:
                self.update({'order_line': new_lines})
