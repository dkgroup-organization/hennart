
import openerp.addons.decimal_precision as dp
from odoo import SUPERUSER_ID
from odoo import netsvc
import unicodedata
import time
import datetime
from dateutil.relativedelta import relativedelta
import base64
from odoo import api,fields,models,_
import odoo.addons.decimal_precision as dp
from datetime import date
from datetime import datetime
import time
import base64
from odoo import api, fields, models,  tools
from odoo.modules import get_module_resource
import base64



class images_easy_sale(models.Model):
    _name = "images.easy.sale"

    image_light_green = fields.Binary('Green light')
    image_light_orange = fields.Binary('Orange light')
    image_light_red = fields.Binary('Red light')

    # @api.model
    # def _get_default_image_green(self):
    #         image = False
    #         img_path = get_module_resource('smiley_costumer', 'static/img', 'smiley_vert.png')
    #         if img_path:
    #             with open(img_path, 'rb') as f: # read the image from the path
    #                  image = f.read()
    #             if image: # if the file type is .jpg then you don't need this whole if condition.
    #                image = tools.image_colorize(image) 
    #                return tools.image_resize_image_big(base64.b64encode(image))
    # @api.model
    # def _get_default_image_orange(self):
    #         image = False
    #         img_path = get_module_resource('smiley_costumer', 'static/img', 'smiley_vert.png')
    #         if img_path:
    #             with open(img_path, 'rb') as f: # read the image from the path
    #                  image = f.read()
    #             if image: # if the file type is .jpg then you don't need this whole if condition.
    #                image = tools.image_colorize(image) 
    #                return tools.image_resize_image_big(base64.b64encode(image))  
    # @api.model
    # def _get_default_image_red(self):
    #         image = False
    #         img_path = get_module_resource('smiley_costumer', 'static/img', 'smiley_vert.png')
    #         if img_path:
    #             with open(img_path, 'rb') as f: # read the image from the path
    #                  image = f.read()
    #             if image: # if the file type is .jpg then you don't need this whole if condition.
    #                image = tools.image_colorize(image) 
    #                return tools.image_resize_image_big(base64.b64encode(image))

