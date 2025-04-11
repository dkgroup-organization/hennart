from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime

class ResPartnerCadence(models.Model):
    _inherit = 'res.partner.cadence'

    @api.depends('product_id', 'week_number', 'partner_id')
    def compute_cadence(self):
        """ get the sale frequency of the product, futur function in customize_account"""
        week_horizon = self.env['res.partner.cadence'].get_week_horizon()

        for line in self:
            if not (line.product_id and line.week_number and line.partner_id):
                line.name = '...'
            else:
                week_number_start = line.week_number - week_horizon
                partner_domain = line.partner_id.get_cadence_sql_domain()
                sql = f"""
                SELECT am.week_number ,sum(aml.uom_qty) 
                FROM account_move_line aml, account_move am 
                WHERE aml.move_id = am.id
                AND am.move_type = 'out_invoice'
                AND aml.product_id = {line.product_id.id}
                AND (am.partner_id in {partner_domain} OR am.partner_shipping_id in {partner_domain})
                AND am.week_number >= {week_number_start} AND am.week_number <= {line.week_number}
                GROUP BY am.week_number
                """
                self.env.cr.execute(sql)
                result_sql = self.env.cr.fetchall()
                qty_by_week = {}
                for raw in result_sql:
                    if raw[1] >= 1:
                        qty_by_week[raw[0]] = f'{int(raw[1])}'

                cadence_table = '<table style="border-collapse: collapse; width: 100%; table-layout: fixed;"><tr>'
                style_td = "border-left: 1px solid grey; width:7.6%; padding-left: 5px; padding-right: 5px;"
                style_text = " font-weight: bold; text-align: center;"
                for week in range(line.week_number - 1, week_number_start - 1, -1):
                    if qty_by_week.get(week):
                        cadence_table += f'<td style="{style_td + style_text}">{qty_by_week[week]}</td>'
                    else:
                        cadence_table += f'<td style="{style_td}"></td>'
                cadence_table += '</tr></table>'
                line.name = cadence_table

