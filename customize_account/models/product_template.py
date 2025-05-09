# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def compute_current_cost_price(self):
        """ compute current stock value """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for product in self:
            # Product in stock
            if product.base_unit_count > 1:
                base_product_ids = product.base_product_tmpl_id.product_variant_ids.ids
            else:
                base_product_ids = product.product_variant_ids.ids

            # Récupérer les lignes de stock avec leur valeur
            quant_ids = self.env['stock.quant'].search([
                ('product_id', 'in', base_product_ids),
                ('location_id.usage', '=', 'internal'),
                ('lot_id', '!=', False)
            ])

            # Récupérer les lignes de facture d'achat pour ce produit des 6 derniers mois
            invoice_line_lot = self.env['account.move.line.lot'].search([
                ('product_id', 'in', base_product_ids),
                ('account_move_line_id.move_id.move_type', '=', 'in_invoice'),  # Filtre les factures d'achat
                ('account_move_line_id.move_id.state', '=', 'posted'),  # Seulement les factures validées
                ('lot_id', 'in', quant_ids.lot_id.ids)
            ])

            # Calcul du prix moyen pondéré
            total_cost_quantity = 0.0
            total_cost_weight = 0.0
            total_quantity = 0.0
            total_weight = 0.0

            for line in invoice_line_lot.account_move_line_id:
                if line.product_uom_id == uom_weight:
                    total_weight += line.quantity
                    total_cost_weight += line.price_subtotal
                else:
                    total_quantity += line.quantity
                    total_cost_quantity += line.price_subtotal

            if total_weight:
                product.current_cost_price = total_cost_weight / total_weight
            elif total_quantity:
                product.current_cost_price = total_cost_quantity / total_quantity
            else:
                product.current_cost_price = 0.0

    def compute_average_cost_price(self):
        """ Compute the average cost price """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        date_now = fields.Datetime.now()

        for product in self:
            # Check last computing date < 10 mn
            if (date_now - product.cost_price_date).total_seconds() < 600:
                product.average_cost_price = product.average_cost_price

            elif product.bom_ids:
                average_cost_price = 0.0
                for line in product.component_price:
                    line.composant_tmpl_id.compute_average_cost_price()
                    average_cost_price += line.average_cost_price

                product.average_cost_price = average_cost_price / product.base_unit_count
                product.cost_price_date = date_now
            else:
                # Définir la date de début des 6 derniers mois
                date_six_months_ago = fields.Date.to_date(fields.Date.context_today(self)) - timedelta(days=180)

                if product.base_unit_count > 1:
                    base_product_ids = product.base_product_tmpl_id.product_variant_ids.ids
                else:
                    base_product_ids = product.product_variant_ids.ids

                # Récupérer les lignes de facture d'achat pour ce produit des 6 derniers mois
                invoice_lines = self.env['account.move.line'].search([
                    ('product_id', 'in', base_product_ids),
                    ('move_id.move_type', '=', 'in_invoice'),  # Filtre les factures d'achat
                    ('move_id.state', '=', 'posted'),  # Seulement les factures validées
                    ('move_id.invoice_date', '>=', date_six_months_ago)
                ])
                # Calcul du prix moyen pondéré
                total_cost_quantity = 0.0
                total_cost_weight = 0.0
                total_quantity = 0.0
                total_weight = 0.0

                for line in invoice_lines:
                    if line.product_uom_id == uom_weight:
                        total_weight += line.quantity
                        total_cost_weight += line.price_subtotal
                    else:
                        total_quantity += line.quantity
                        total_cost_quantity += line.price_subtotal
                        total_weight += line.weight or line.product_id.weight

                if product.uos_id == uom_weight:
                    if total_weight:
                        product.average_cost_price = total_cost_weight / total_weight
                    else:
                        product.average_cost_price = 0.0
                elif total_quantity:
                    product.average_cost_price = total_cost_quantity / total_quantity
                else:
                    product.average_cost_price = 0.0

                if total_quantity:
                    product.average_weight = total_weight / total_quantity
                else:
                    product.average_weight = product.weight

                product.cost_price_date = date_now