# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class ProductPackagingInherit(models.Model):
    _inherit = 'product.packaging'

    @api.model_create_multi
    def create(self, values_list):
        for vals in values_list:
            _logger.info("vals to create %s" %(vals))
            if 'name' not in vals or not vals['name']:
                _logger.info("create record %s" %vals)
                p_name = vals['barcode'] and '[' + vals['barcode'] + '] ' or ''
                type = self.env['stock.package.type'].browse(vals['package_type_id'])
                p_name += type.name
                p_name += vals['qty'] > 0 and ' %s' %str(int(vals['qty'])) or ''
                vals['name'] = p_name
                vals['company_id'] = 1
        return super(ProductPackagingInherit,self).create(values_list)