# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class ProductPackagingInherit(models.Model):
    _inherit = 'product.packaging'

    @api.model_create_multi
    def create(self, values_list):
        for vals in values_list:
            if 'name' not in vals or not vals['name']:
                p_name = 'colis'
                p_name += " ({})".format(vals.get('qty', 0))
                vals['name'] = p_name
            vals['company_id'] = 1
        return super(ProductPackagingInherit,self).create(values_list)

    def name_get(self):
        """ Return the quantity in package
        """
        res = []
        for package in self:
            name = package.name or 'colis'
            res.append((package.id, "{} ({})".format(name, int(package.qty))))
        return res
