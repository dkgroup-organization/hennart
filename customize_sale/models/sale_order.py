# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from datetime import date, timedelta, datetime
from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_delivered = fields.Datetime("delivered date", help="Customer delivered date")

    @api.onchange('partner_id')
    def onchange_partner_id_dates(self):
        for rec in self:
            delivered_date = False
            date_entrepot = False
            carrier = False
            today1 = datetime.now()

            if rec.partner_id.appointment_delivery_ids:
                app = rec.partner_id.appointment_delivery_ids[0]
                rec.carrier_id = rec.partner_id.appointment_delivery_ids[0].carrier_id.id
                load_time = rec.partner_id.appointment_delivery_ids[0].load_time

                if today1 > self.timezone_2_utc(today1, 12):
                    today1 += timedelta(days=1)

                while today1.weekday() != int(app.load_day):
                    # 0 for monday
                    today1 += timedelta(days=1)
                date_entrepot = today1
                today2 = date_entrepot

                while today2.weekday() != int(app.delivery_day):
                    today2 += timedelta(days=1)
                delivered_date = today2

                print(date_entrepot, delivered_date)
                rec.date_delivered = self.timezone_2_utc(delivered_date, load_time)
                rec.commitment_date = self.timezone_2_utc(date_entrepot, load_time)

    @api.model
    def timezone_2_utc(self, date, time, timezone="Europe/Paris"):
        """ return datetime with time (in float) with conversion in  timezone to UTC
        use partner.crm.appointment.timezone_2_utc function"""
        return self.env['partner.crm.appointment'].timezone_2_utc(date, time, timezone=timezone)

    #@api.onchange('partner_id')
    def _onchange_partner_id(self):
        # Clear the history lines when the partner is changed
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
                    self.order_line += self.env['sale.order.line'].create({
                        'product_id': product_id,
                        'order_id': self.id
                    })