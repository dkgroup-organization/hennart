
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


class param_late_paiement(models.Model):
    _name = "param.late.paiement"

    limit1 = fields.Integer('Limit 1')
    limit2 = fields.Integer('Limit 2')
    partner_id = fields.Many2one('res.partner', 'Customer')
    level = fields.Selection([('green', 'Green'), ('orange', 'Orange'), ('red', 'Red')], 'Level')
