from odoo import models, api, Command

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('date_delivered')
    def _onchange_date_delivered(self):
        if self.date_delivered:
            promotions = self.env['sale.promotion'].search([
                ('date_start', '<=', self.date_delivered),
                ('date_end', '>=', self.date_delivered)
            ])

            new_lines = []
            for promo in promotions:
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
