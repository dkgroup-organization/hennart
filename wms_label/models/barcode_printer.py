##############################################################################
#                                                                            #
#   OpenERP Module                                                           #
#   Copyright (C) 2016 OpenCrea <joannes.landy@opencrea.fr>                  #
#                                                                            #
#   This program is free software: you can redistribute it and/or modify     #
#   it under the terms of the GNU Affero General Public License as           #
#   published by the Free Software Foundation, either version 3 of the       #
#   License, or (at your option) any later version.                          #
#                                                                            #
#   This program is distributed in the hope that it will be useful,          #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#   GNU Affero General Public License for more details.                      #
#                                                                            #
#   You should have received a copy of the GNU Affero General Public License #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
#                                                                            #
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

import cups
import subprocess
import shlex
import sys

from datetime import datetime
import time
import os
import codecs
import logging
logger = logging.getLogger('BARCODES PRINTERS')


class BarcodesPrinters(models.Model):
    _name = "barcodes.printers"

    def print_test_page(self):
        
        self.env.context
        conn = cups.Connection()

        for printer in self:
            
            conn.printTestPage(printer.printer_id.system_name.encode())

        return True

    def print_zpl_label(self, label_template_content='', ido=False):
            context = self.env.context
            pp = self.env['labels.templates'].browse(ido)
            date_printer = time.strftime("%Y%m%d")
            #Add zpl header
            label_template_content = chr(16) + 'CT~~CD,~CC^~CT~\n' + str(label_template_content)
            filename = '/tmp/workfile_' + str(pp.barcode_printer_id.id) + str(self.env.user.id) + date_printer + '.zpl'
            file_ = open(filename, 'w')
            file_.write(label_template_content)
            file_.close()
            
            #print the file
            commands = 'lp -d %s %s' % (pp.barcode_printer_id.system_name, filename)
            args = shlex.split(commands)
            
            # raise UserError(commands)
            try:
                subprocess.call(args)
                raise UserError('Nice one')
            except :
                logger.warning("Failed to execute lp command")
                raise UserError('Action cancel ! Fail to execute lp command ')

            #os.remove(file_name)

            return True

    def _get_company_id(self):
        context = self.env.context
        
        return self.env.user.company_id.id

    def _update_info(self):
        for printer in self:
            printer.system_name = ''
            if printer.printer_id:
                printer.system_name = printer.printer_id.system_name


    system_name = fields.Char(compute="_update_info", size=256, string='Name')
    name = fields.Char('Description', size=80, required=True)
    printer_id = fields.Many2one('printing.printer', 'Printer', required=True)
    barcode = fields.Char('Barcode', size=32)
    company_id = fields.Many2one('res.company', 'Company', required=True)

    

    _defaults = {
        'company_id': _get_company_id,
        }

