# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval

from datetime import date, timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision


class Sale_Order(models.Model):
    _inherit = 'sale.order'


    date_delivered = fields.Datetime(
        "Date de livraison Client", store=True,
        help="Date de livraison Client")

    @api.onchange('partner_id')
    def onchange_partner_id_dates(self):
        for rec in self:
            delivered_date = False
            date_entrepot = False
            carrier = False
            today1 = datetime.now()
            

            if rec.partner_id.appointment_delivery_ids:
                app = rec.partner_id.appointment_delivery_ids[0]

                if today1.weekday() == int(app.load_day):
                  if  today1.hour < 11:
                    while today1.weekday() != int(app.load_day): #0 for monday
                      today1 += timedelta(days=1)
                    date_entrepot = today1
                    today2 = date_entrepot

                    while today2.weekday() != int(app.delivery_day): #0 for monday
                      today2 += timedelta(days=1)
                    delivered_date = today2

                    rec.date_delivered = delivered_date
                    rec.commitment_date = date_entrepot
                    rec.carrier_id = rec.partner_id.appointment_delivery_ids[0].carrier_id.id
                    user_id = rec.user_id.id
                  else:
                    today1 += timedelta(days=1)
                    while today1.weekday() != int(app.load_day): #0 for monday
                      today1 += timedelta(days=1)
                    date_entrepot = today1
                    today2 = date_entrepot

                    while today2.weekday() != int(app.delivery_day): #0 for monday
                      today2 += timedelta(days=1)
                    delivered_date= today2

                    rec.date_delivered = delivered_date
                    rec.commitment_date = date_entrepot
                    rec.carrier_id = rec.partner_id.appointment_delivery_ids[0].carrier_id.id
                    user_id = rec.user_id.id

                else:
                    while today1.weekday() != int(app.load_day): #0 for monday
                      today1 += timedelta(days=1)
                    date_entrepot = today1
                    today2 = date_entrepot

                    while today2.weekday() != int(app.delivery_day): #0 for monday
                      today2 += timedelta(days=1)
                    delivered_date = today2

                    rec.date_delivered = delivered_date
                    rec.commitment_date = date_entrepot
                    rec.carrier_id = rec.partner_id.appointment_delivery_ids[0].carrier_id.id
                    user_id = rec.user_id.id




class Stock_picking(models.Model):
    _inherit = 'stock.picking'


    date_delivered = fields.Datetime(
        "Date de livraison Client",compute='_compute_date_deliverd',
        help="Date de livraison Client")

    def _compute_date_deliverd(self):
        for order in self:
            if order.sale_id:
               order.date_delivered = order.sale_id.date_delivered
            else:
                order.date_delivered = False



