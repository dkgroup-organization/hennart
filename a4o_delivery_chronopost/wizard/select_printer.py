# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CpstSelectPrinter(models.TransientModel):
    _name = 'cpstselect.printer'
    _description = 'Printer Selection Wizard'

    printer_id = fields.Many2one(
        comodel_name='printing.printer',
        default=lambda self: self._context.get('default_printer_id'),
        string='Printer',
        help="Printer")

    def cpst_set_printer(self):
        cpst_carrier_id = self.env.context.get('carrier_id')
        if cpst_carrier_id:
            cpst_carrier = self.env['delivery.carrier'].browse(cpst_carrier_id)
            if self.printer_id:
                cpst_carrier.write({
                        'cpst_printer_id': self.printer_id.id,
                        'cpst_printer': self.printer_id.name,
                        'cpst_printer_name': "printing.printer,%s" % (
                            str(self.printer_id.id)),
                        })
