
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


class images_easy_sale(models.Model):
    _name = "images.easy.sale"

    image_light_green = fields.Binary('Green light')
    image_light_orange = fields.Binary('Orange light')
    image_light_red = fields.Binary('Red light')
