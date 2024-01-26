# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class StockSSCC(models.Model):
    _inherit = 'stock.sscc'

    def print_label(self, printer=None, label_id=None):
        """ print zpl label """
        label_id = label_id or self.env['printing.label.zpl2'].search([('model_id.model', '=', self._name)])
        if printer and label_id:
            for sscc in self:
                label_id.print_label(printer, sscc)

        for sscc in self:
            print('--------------------------', sscc)
            test = """{name}{country}
            {date}
            {partner_name}{street}{street2}{zip}{city} 
                    {partner_name}
                    {carrier_zone}
                    {nb_sscc} / {nb_total_sscc}""".format(
                name=sscc.name,
                partner_name=sscc.picking_id.partner_id.name or '',
                carrier_zone=sscc.picking_id.partner_id.carrier_zone or '',
                street=sscc.picking_id.partner_id.street or '',
                street2=sscc.picking_id.partner_id.street2 or '',
                zip=sscc.picking_id.partner_id.zip or '',
                city=sscc.picking_id.partner_id.city or '',
                country=sscc.picking_id.partner_id.country_id.name or '',
                nb_sscc=sscc.nb_sscc,
                nb_total_sscc=sscc.nb_total_sscc,
                date=sscc.picking_id.date_delivered and sscc.picking_id.date_delivered.strftime('%d/%m/%Y') or '')
            print(test)
