from odoo import models, fields ,api, _
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

    def get_delivery_hours(self, date):
        """ Return the hour of delivery carrier load by day """
        self.ensure_one()
        # get the days of week of date
        # get the hours of this day of week by field dow_0 .... 6
        # If not hour default is 12:00?
        # return date with good hour
        return date
