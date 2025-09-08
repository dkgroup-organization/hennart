
from odoo import api, fields, models, _
from datetime import date, timedelta


class partner_delivery_appointment(models.Model):

    _name = "partner.delivery.appointment"
    _description = "Partner delivery Appointement"


    load_day =fields.Selection([
                        ('0', 'Monday'),
                        ('1', 'Tuesday'),
                        ('2', 'Wednesday'),
                        ('3', 'Thursday'),
                        ('4', 'Friday'),
                        ('5', 'Saturday'),
                        ('6', 'Sunday'),
                        ], 'Load day', index=True)
    load_time = fields.Float('Load Time')
    delivery_day = fields.Selection([
                        ('0', 'Monday'),
                        ('1', 'Tuesday'),
                        ('2', 'Wednesday'),
                        ('3', 'Thursday'),
                        ('4', 'Friday'),
                        ('5', 'Saturday'),
                        ('6', 'Sunday'),
                           ], 'Delivery Day', index=True)

    delivery_time = fields.Float('Delivery Time')
    partner_id = fields.Many2one('res.partner', 'Customer')
    carrier_id = fields.Many2one("delivery.carrier", "Delivery Method")


