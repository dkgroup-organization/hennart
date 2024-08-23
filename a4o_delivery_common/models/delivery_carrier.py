# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import api, models, fields
from odoo.addons.resource.models.resource import float_to_time
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

WEEKDAY = [
    ('1', 'Monday'),
    ('2', 'Tuesday'),
    ('3', 'Wednesday'),
    ('4', 'Thursday'),
    ('5', 'Friday'),
    ('6', 'Saturday'),
    ('7', 'Sunday'),
]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    sender_id = fields.Many2one('res.partner', 'Sender',
        default=lambda self: self.env.company.partner_id,
        help="Select the partner that will be used as sender when requesting "
        "a label from the carrier.")
    country_origin_id = fields.Many2one('res.country',
        string='Default Country of Origin', ondelete='restrict',
        help="Country of origin of the default product (if not indicated on "
        "the product) used in CN22/CN23.\n"
        "Beware! it is preferable to use Odoo's intrastat modules or a module "
        "from a partner to add this information to each product.")
    availability_day = fields.Selection([
            ('always', 'Always'),
            ('interval', 'Interval'),
            ], string="Days of availability", default='always',
        help="Allows you to define the period of availability of the delivery "
        "method.")
    from_day = fields.Selection(WEEKDAY, string='From Day')
    from_time = fields.Float(string="From Time")
    to_day = fields.Selection(WEEKDAY, string='To Day')
    to_time = fields.Float(string="To Time")

    @api.model
    def cron_get_sending_package_status(self):
        """Cron called regularly to check the status of the shipment."""
        self.get_sending_package_status()

    @api.model
    def get_sending_package_status(self):
        delivery_types = set(self.search([]).mapped('delivery_type'))
        for delivery_type in delivery_types:
            _logger.debug("[get_sending_package_status] Delivery type: "
                "%s", delivery_type)
            method = getattr(
                self, '%s_get_sending_package_status' % delivery_type, None)
            if method:
                method()

    def available_carriers(self, partner):
        carrier_ids = super().available_carriers(partner)
        to_check = carrier_ids.filtered(
            lambda c: c.availability_day == 'interval')
        for carrier in to_check:
            now = datetime.now()
            from_date = self.day_time_to_datetime(carrier.from_day,
                carrier.from_time)
            to_date = self.day_time_to_datetime(carrier.to_day,
                carrier.to_time)
            if not (from_date <= now <= to_date):
                carrier_ids -= carrier
        return carrier_ids

    def day_time_to_datetime(self, day, time):
        """
        @param day: Day of the week (isoweekday)
        @param time: The scheduled time in float
        @return: A datetime, is the date of the next day of the week chosen
                from today, with the scheduled time.
        """
        hour = float_to_time(time).hour
        minute = float_to_time(time).minute
        today = datetime.today()
        weekday = today.isoweekday()
        result = today + timedelta(days=int(day) - weekday,
            hours=hour - today.time().hour,
            minutes=minute - today.time().minute)
        return result
