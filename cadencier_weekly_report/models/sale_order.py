from odoo import fields, models, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    history_lines = fields.One2many('cadence.history.lines', 'sale_order_id', string='History Lines')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # Clear the history lines when the partner is changed
        self.history_lines = False
        # If the partner is not null, get the order lines for the past 13 weeks
        if self.partner_id:
            date_from = datetime.today() - timedelta(weeks=13)
            order_lines = self.env['sale.order.line'].search([
                ('order_id.partner_id', '=', self.partner_id.id),
                ('order_id.date_order', '>=', date_from.date())
            ])
            # Get the product ids of the order lines
            product_ids = order_lines.mapped('product_id').ids
            for product_id in product_ids:
                qty_by_week = {}
                # Loop through the past 13 weeks
                for week in range(1, 14):
                    date_to = datetime.today() - timedelta(weeks=week-1)
                    date_from = datetime.today() - timedelta(weeks=week)
                    # Get the quantity sold for the product for the current week
                    qty = sum(order_lines.filtered(lambda l: l.product_id.id == product_id and date_from.date() <= l.order_id.date_order.date() <= date_to.date()).mapped('product_uom_qty'))
                    # If the quantity is not zero, add it to the quantity by week dictionary
                    if qty != 0:
                        qty_by_week['{}'.format(week)] = qty

                # If there is data for the product, create a table to display the quantity sold by week
                if qty_by_week:
                    cadence_table = '<table style="border-collapse: collapse; width: 100%; table-layout: fixed;"><tr>'
                    for week in range(1, 14):
                        qty = qty_by_week.get('{}'.format(week), '')
                        if qty != '':
                            qty_str = str(int(qty))
                            cadence_table += '<td style="border-left: 1px solid black; width:7.6%; font-weight: bold; text-align: center; padding: 5px;">{}</td>'.format(qty_str)
                        else:
                            cadence_table += '<td style="border-left: 1px solid black; width:7.6%; padding: 5px;"></td>'
                    cadence_table += '</tr></table>'

                    # Create a history line record for the product with the quantity sold by week
                    self.history_lines += self.env['cadence.history.lines'].create({
                        'product_id': product_id,
                        'cadence': cadence_table,
                        'sale_order_id': self.id
                    })