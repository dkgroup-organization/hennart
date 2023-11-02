# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def button_test(self):
        """ Test futur function"""
        #"printing.label.zpl2"

        for line in self:
            line.print_label()



    def print_label(self, printer=None):
        """ Print label"""
        if not printer:
            printer = self.env['printing.printer'].search([('system_name', '=', 'RECEPTION')], limit=1)

        print('\n--------print_label--------------', dir(self))

        model_id = self.env['ir.model'].search([('model', '=', '')])

        label_ids = self.env['printing.label.zpl2'].search([('model_id', '=', self._model_id.id)])




    def print_label2(self, printer, record, page_count=1, **extra):

        "printing.label.zpl2"
        for label in self:
            if record._name != label.model_id.model:
                raise UserError(
                    _("This label cannot be used on {model}").format(model=record._name)
                )
            # Send the label to printer
            label_contents = label._generate_zpl2_data(
                record, page_count=page_count, **extra
            )
            printer.print_document(
                report=None, content=label_contents, doc_format="raw"
            )
        return True
