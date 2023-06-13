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
import logging
_logger = logging.getLogger(__name__)
from mako.template import Template as MakoTemplate

CODE_CP850 = {'Ç': '\80', 'ü': '\81', 'é': '\82', 'â': '\83', 'ä': '\84', 'à': '\85', 'å': '\86', 'ç': '\87', 'ê': '\88', 'ë': '\89',
'è': '\8A', 'ï': '\8B', 'î': '\8C', 'ì': '\8D', 'Ä': '\8E', 'Å': '\8F', '°': '\F8'}


class labels_templates(models.Model):

    _name = "labels.templates"
    _description = 'Labels Templates'

    def _get_company_id(self):
        
        return self.env.user.company_id.id

    def render_zpl(self, res_id=False):
      context =  self.env.context
      res = ''
      for label in self:
        user = self.env.user
        if res_id:
            record = self.env[label.model_id.model].browse(res_id)
        else:
            record = None

        res = MakoTemplate(label.label_zpl).render_unicode(object=record,
                                                       user=user,
                                                       ctx=context,
                                                       format_exceptions=True)

        if res:
            res = res.encode('utf-8')
            #For ZEBRA native police in CP850 code, replace accentuated char
            for key in CODE_CP850.keys():

                res = res.replace(key.encode(), CODE_CP850[key].encode())
        else:
            res = '^XA\n^XZ'

        return res

    def button_print(self):
        
        for label in self:
            if label.barcode_printer_id:
                if label.res_id:
                    self.print_label([label.res_id], label.barcode_printer_id.id)

    def print_label(self, res_ids=[], printer_id=False):
    
        context =  self.env.context
        printer_obj = self.env['barcodes.printers']
        res_ids = isinstance(res_ids, (int)) and [res_ids] or res_ids

        for label in self:
            if not printer_id and label.barcode_printer_id:
                printer_id = label.barcode_printer_id.id
            if printer_id:
                for res_id in res_ids:
                    template_content = self.render_zpl(res_id)
                    printer_obj.print_zpl_label(template_content,label.id)

        return True


    name = fields.Char("Name", size=65, required=True)
    company_id = fields.Many2one('res.company', 'Company')
    model_id = fields.Many2one('ir.model', 'Model', required=True,ondelete='cascade')
    label_zpl = fields.Text('Label zpl')
    barcode_printer_id = fields.Many2one('barcodes.printers', 'Default Printer')
    res_id = fields.Integer('Test id')


    _defaults = {
        'company_id': _get_company_id,
    }

