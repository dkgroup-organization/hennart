

import openerp.addons.decimal_precision as dp
from odoo import SUPERUSER_ID
from odoo import netsvc
import unicodedata
import time
import datetime
from dateutil.relativedelta import relativedelta
import pytz
import base64
from odoo import api,fields,models,_
import odoo.addons.decimal_precision as dp
from datetime import date
from datetime import datetime
import time


class res_partner(models.Model):
    _inherit = "res.partner"


    @api.depends('invoice_ids')
    def _update_info(self):
        account_invoice_object = self.env['account.move']
        today_date = date.today()  
        current_date = str(today_date)

        for partner in self:

            partner.late_paiement = 0
            if partner.is_company:
                 if partner.invoice_ids: 
                   for invoice_id in partner.invoice_ids:
                     if invoice_id.move_type == 'out_invoice' and invoice_id.payment_state == 'not_paid':  
                        date_due = datetime.strptime(str(invoice_id.invoice_date_due), '%Y-%m-%d')
                        delay = int((today_date - invoice_id.invoice_date_due).days)
                        if partner.late_paiement < delay:
                            partner.late_paiement = delay
    @api.depends('late_paiement')
    def _image_late_paiement(self):
        for partner in self:
            partner._update_info()
            i = partner.late_paiement
            param_customer_ids = self.env['param.late.paiement'].search([('partner_id', '=', partner.id), ('limit1', '<=', i), ('limit2', '>=', i)])
            if not param_customer_ids:
                param_customer_ids = self.env['param.late.paiement'].search([('partner_id', '=', False),('limit1', '<=',i),('limit2', '>=', i)],limit=1)
            if not param_customer_ids:
                partner.image_late_paiement = False
            else:
                    image_late_paiement_obj = self.env['images.easy.sale'].browse(1)

                    if param_customer_ids.level == 'red':
                        partner.image_late_paiement = image_late_paiement_obj.image_light_red
                    elif param_customer_ids.level == 'orange':
                        partner.image_late_paiement = image_late_paiement_obj.image_light_orange
                    else:
                        partner.image_late_paiement = image_late_paiement_obj.image_light_green

    image_late_paiement = fields.Binary(compute="_image_late_paiement", string='Image for late paiement')
    late_paiement = fields.Integer(compute="_update_info", string='Late paiement',store=True)
