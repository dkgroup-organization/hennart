import logging
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta
from stdnum.vatin import is_valid

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _inherit = "intrastat.product.declaration"

    def _prepare_invoice_domain(self):
        """ filtered invoice         """
        domain = super()._prepare_invoice_domain()
        domain.append(("partner_id.exclude_from_intrastat", "!=", True))
        return domain

    def _is_product(self, invoice_line):
        """ filtered product         """
        res = super()._is_product(invoice_line)
        if invoice_line.product_id.exclude_from_intrastat:
            return False
        else:
            return res
