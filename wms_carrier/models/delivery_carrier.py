from odoo import models, fields ,api, _
from odoo.exceptions import ValidationError
import time
import datetime

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    code = fields.Char('Code', size=10)
    edi_sscc_csv = fields.Boolean('SSCC CSV Nagel')
    edi_csv = fields.Boolean('CSV file')
    edi_pdf = fields.Boolean('PDF file')
    edi_chronopost = fields.Boolean('Chronopost')
    edi_partner_id = fields.Many2one('res.partner', 'Contact Email')

    edi_subject = fields.Char('Subject', size=128)
    edi_body = fields.Html('Body')

    sftp_server = fields.Char('SFTP Server address')
    sftp_user = fields.Char('SFTP User')
    sftp_password = fields.Char('SFTP password')
    sftp_dir = fields.Char('SFTP directory')

    dow_0 = fields.Float('Monday')
    dow_1 = fields.Float('Tuesday')
    dow_2 = fields.Float('Wednesday')
    dow_3 = fields.Float('Thursday')
    dow_4 = fields.Float('Friday')
    dow_5 = fields.Float('Saturday')
    dow_6 = fields.Float('Sunday')

    @api.constrains('dow_0', 'dow_1', 'dow_2', 'dow_3', 'dow_4', 'dow_5', 'dow_6')
    def _check_dow_values(self):
        for record in self:
            for weekday in range(7):
                if not (0 <= getattr(self, f'dow_{weekday}') < 24):
                    raise ValidationError("This time must be between 0 and 24.")

    def get_delivery_hours(self, date):
        """ Return the hour of delivery carrier load by day """
        self.ensure_one()
        weekday = date.weekday()
        if hasattr(self, f'dow_{weekday}'):
            delivery_hour = getattr(self, f'dow_{weekday}')
        else:
            delivery_hour = 12.00

        hour = int(delivery_hour)
        minute = int(float(hour) - delivery_hour) * 60
        date = date.replace(hour=hour, minute=minute)
        return date
