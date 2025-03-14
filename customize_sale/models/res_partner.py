# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cadence = fields.Html(string="Cadencier", compute="compute_cadence")


    def compute_cadence(self):
        # cadencier
        # Create the name of the column
        for rec in self:
            # If there is data for the product, create a table to display the quantity sold by week
            cadence_table = '<div id="cadence" class="col-10 ms-auto me-auto"> <table class="table table-bordered"><thead class="table-light"><tr><th style="font-weight: bold; text-align: center;border-left: 1px solid grey; width:30%;"> Produit </th>'
            style_td = 'border-left: 1px solid grey; width:4%;'
            style_text = ' font-weight: bold; text-align: center;'
            date_start = datetime.now()
            date_start = date_start - timedelta(days=date_start.weekday())
            date_from = datetime.now() - timedelta(weeks=13)
            for week in range(0, 13):
                cadence_table += '<th style="%s">%s</th>' %(style_td + style_text, str(-week))
            cadence_table +='</tr></thead><tbody>'
            condition = [
                ('move_id.partner_id', '=', rec.id),
                ('move_id.invoice_date', '<', date_start),
                ('move_id.invoice_date', '>=', date_from),
                ('move_id.state', '!=', 'cancel'),
                ('move_id.move_type', '=', 'out_invoice'),
            ]
            invoice_lines = self.env['account.move.line'].search(condition)
            for product_id in invoice_lines.mapped('product_id'):
                cadence_table += '<tr><td>[%s] %s </td>' %(product_id.default_code, product_id.name)
                pack = product_id.base_unit_count if product_id.base_unit_count> 0.0 else 1
                for week in range(0, 13):
                    date_to = date_start - timedelta(weeks=week - 1)
                    date_from = date_start - timedelta(weeks=week)
                    qty = sum(invoice_lines.filtered(lambda
                                                     l: l.product_id.id == product_id.id
                                                        and date_from.date() <= l.move_id.invoice_date <= date_to.date()).mapped('uom_qty'))
                    qty_text = int(qty / pack) if qty > 0.0 else ""
                    cadence_table += '<td> %s </td>' %(qty_text)
                cadence_table +='</tr>'
            cadence_table += '</tbody></table></div>'
            rec.cadence = cadence_table
