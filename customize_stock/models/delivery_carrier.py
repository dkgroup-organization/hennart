from odoo import models, fields ,api, _
import time
import datetime

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    def get_delivery_hours(self, date):
        """ Return the hour of delivery carrier load by day """
        self.ensure_one()
        # futur function
        # If not hour default is 12:00?
        date = date.replace(hour=12, minute=59)
        return date


