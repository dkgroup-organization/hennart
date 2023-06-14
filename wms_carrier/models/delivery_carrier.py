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
    sftp_server = fields.Char('SFTP Server address')
    sftp_user = fields.Char('SFTP User')
    sftp_password = fields.Char('SFTP password')
    sftp_dir = fields.Char('SFTP directory')
    edi_subject = fields.Char('Subject', size=128)
    edi_body = fields.Html('Body')
