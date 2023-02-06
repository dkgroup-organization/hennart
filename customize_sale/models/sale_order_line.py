# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_customer_lead(self):
        """ The customer lead is more complexe in this project, It depend on location of customer """
        self.customer_lead = 0.0