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
