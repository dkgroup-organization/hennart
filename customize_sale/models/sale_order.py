# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_delivered = fields.Datetime("delivered date", help="Customer delivered date")

    @api.model
    def timezone_2_utc(self, date, time, timezone="Europe/Paris"):
        """ return datetime with time (in float) with conversion in  timezone to UTC
        use partner.crm.appointment.timezone_2_utc function"""
        return self.env['partner.crm.appointment'].timezone_2_utc(date, time, timezone=timezone)

    def onchange_partner_id_dates(self):
        """ update commitment_date """
        self.ensure_one()
        res = {}
        today1 = datetime.now()
        if self.partner_id.appointment_delivery_ids:
            app = self.partner_id.appointment_delivery_ids[0]
            res['carrier_id'] = self.partner_id.appointment_delivery_ids[0].carrier_id.id
            load_time = self.partner_id.appointment_delivery_ids[0].load_time

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

            res['date_delivered'] = self.timezone_2_utc(delivered_date, load_time)
            res['commitment_date'] = self.timezone_2_utc(date_entrepot, load_time)
        return res

    @api.onchange('partner_id')
    def onchange_partner_id_cadence(self, date_order=None):
        # Clear the history lines when the partner is changed
        # If the partner is not null, get the order lines for the past 13 weeks
        nb_week = 13

        self.ensure_one()
        line_vals = []
        res = self.onchange_partner_id_dates()
        commitment_date = res.get('commitment_date') or datetime.today()

        if self.state == 'draft' and self.partner_id:
            date_start = commitment_date - timedelta(days=commitment_date.weekday())  # monday
            date_from = date_start - timedelta(weeks=nb_week)
            order_lines = self.env['account.move.line'].search([
                ('move_id.partner_id', 'child_of', self.partner_id.id),
                ('move_id.invoice_date', '<=', date_start),
                ('move_id.invoice_date', '>=', date_from),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '!=', 'cancel')
            ])
            # Get the product ids of the order lines
            product_ids = order_lines.mapped('product_id') - self.order_line.mapped('product_id')
            for product in product_ids:
                if product.sale_ok:
                    line_vals.append(Command.create({
                        'product_id': product.id,
                        'product_template_id': product.product_tmpl_id.id,
                        'product_uom_qty': 0.0,
                    }))
        if line_vals:
            res = {'order_line': line_vals}

        self.update(res)


