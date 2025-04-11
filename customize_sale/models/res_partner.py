# -*- coding: utf-8 -*-
from odoo import api, fields, models
import datetime
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    week_number = fields.Integer('Week number', index=True)
    cadence_ids = fields.One2many('res.partner.cadence', 'partner_id', string='Cadendier')

    def get_cadence_sql_domain(self):
        """ return domain """
        self.ensure_one()
        partner_ids = self.child_ids.filtered(lambda c: not c.is_company)
        partner_ids |= self
        partner_domain = str(partner_ids.ids).replace('[', '(').replace(']', ')')
        return partner_domain

    def compute_cadence(self):
        """ return list of product for cadencier """
        week_horizon = self.env['res.partner.cadence'].get_week_horizon()
        week_number = self.env['res.partner.cadence'].get_week_number()
        week_number_start = week_number - week_horizon

        for partner in self:
            partner.week_number = week_number
            partner_domain = partner.get_cadence_sql_domain()
            partner.cadence_ids.unlink()

            sql = f"""
            SELECT aml.product_id
            FROM account_move_line aml, account_move am, product_product pp
            WHERE aml.move_id = am.id AND aml.product_id = pp.id
            AND am.move_type = 'out_invoice'
            AND (am.partner_id in {partner_domain} OR am.partner_shipping_id in {partner_domain})
            AND am.week_number >= {week_number_start} AND am.week_number <= {week_number}
            GROUP BY aml.product_id
            ORDER BY max(pp.default_code)
            """
            self.env.cr.execute(sql)
            result_sql = self.env.cr.fetchall()
            if not result_sql:
                partner.week_number = None
            for raw in result_sql:
                if raw[0] and raw[0] > 1:
                    product = self.env['product.product'].browse(raw[0])
                    if product.detailed_type == 'product':
                        cadence_vals = {
                            'partner_id': partner.id,
                            'product_id': product.id,
                            'week_number': week_number,
                        }
                        partner.cadence_ids.create(cadence_vals)

    @api.model
    def cron_update_cadencier(self):
        """ Scheduled update """
        week_number = self.env['res.partner.cadence'].get_week_number()
        partner_ids = self.search([
            ('week_number', '!=', False),
            ('cadence_ids', '!=', False),
            ('week_number', '!=', week_number)
        ], limit=100)
        partner_ids.compute_cadence()
