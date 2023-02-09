# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################


from odoo import api, fields, models, _, tools


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @tools.ormcache()
    def _get_default_uos_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('uom.product_uom_unit')

    uos_id = fields.Many2one('uom.uom', string='Unit of Sale',
                             default=_get_default_uos_id, required=True,
                             help="Default unit of Sale used for invoicing.")




