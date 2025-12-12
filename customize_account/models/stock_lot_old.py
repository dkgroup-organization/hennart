
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from collections import defaultdict
import datetime
import time

import logging
_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = 'stock.lot'

    invoice_lot_line_ids = fields.One2many('account.move.line.lot', 'lot_id', string='Invoicing line')
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', store=True, index=True)
    uos_id = fields.Many2one('uom.uom', related='product_id.uos_id', string='Unit of Sale')
    uos_po_id = fields.Many2one('uom.uom', related='product_id.uos_po_id', string="Unité d'achat fournisseur")

    partner_supplier_id = fields.Many2one('res.partner', string='Supplier', compute='get_partner_supplier', readonly=False, store=True)
    partner_supplier_date = fields.Datetime('Supplier Date', compute='get_partner_supplier', readonly=False, store=True)
    partner_supplier_uos_id = fields.Many2one('uom.uom', string='Unit of purchase',  compute='get_partner_supplier', readonly=False, store=True)

    is_weight_based = fields.Boolean(
        string="Basé sur le poids",
        compute="_compute_is_weight_based",
        store=True,
        help="Indique si ce produit ou lot est géré en kilogrammes plutôt qu'à l'unité.",
    )

    @api.depends('uos_po_id')
    def _compute_is_weight_based(self):
        """Détermine si le produit/lot est géré au poids en fonction de l'unité d'achat."""
        for rec in self:
            uom_name = (rec.uos_po_id.name or '').lower()
            rec.is_weight_based = 'kg' in uom_name or 'kilo' in uom_name

    def get_partner_supplier(self):
        """ get supplier """
        for lot in self:
            partner_supplier_id = lot.partner_supplier_id
            partner_supplier_date = lot.partner_supplier_date
            partner_supplier_uos_id = lot.product_id.uos_id

            if lot.upstream_move:
                for move in lot.upstream_move:
                    if move.picking_code == 'incomming':
                        partner_supplier_id = move.picking_id.partner_id
                        partner_supplier_date = move.picking_id.date_done or move.picking_id.scheduled_date
                        partner_supplier_uos_id = move.product_uos
                        break

            elif lot.invoice_lot_line_ids:
                for line in lot.invoice_lot_line_ids:
                    if line.move_type == 'in_invoice':
                        partner_supplier_id = line.account_move_line_id.move_id.partner_id
                        partner_supplier_date = line.account_move_line_id.move_id.invoice_date
                        partner_supplier_uos_id = line.account_move_line_id.product_uos
                        break

            lot.partner_supplier_id = partner_supplier_id
            lot.partner_supplier_date = partner_supplier_date
            lot.partner_supplier_uos_id = partner_supplier_uos_id

    def _get_production_from_lot(self, lot):
        """Retourne la production (OF) associée à un lot, sinon False"""

        return self.env['mrp.production'].search([
                        ('move_finished_ids.move_line_ids.lot_id', '=', lot.id)
                    ], order='date_finished desc', limit=1)



        return self.env['mrp.production'].search([
            ('move_finished_ids.move_line_ids.lot_id', '=', lot.id)
        ], order='date_finished desc', limit=1)

    def _get_bom_for_production(self, production):
        """Retourne la BOM (ou la première BOM de type fabrication si absente)"""
        bom = production.bom_id
        if not bom:
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', production.product_id.product_tmpl_id.id),
                ('type', '=', 'normal'),
            ], order='sequence, id', limit=1)
        return bom

    def _compute_weight_from_bom_recursive_OLD(self, lot, parent_weight):
        """Recalcule le poids réel en remontant récursivement les productions."""
        production = self._get_production_from_lot(lot)
        if not production:
            return parent_weight

        bom = self._get_bom_for_production(production)
        if not bom:
            return parent_weight

        # Prend uniquement les lignes BOM qui correspondent à ce lot
        bom_lines = bom.bom_line_ids.filtered(lambda l: l.product_id == lot.product_id)
        if not bom_lines:
            return parent_weight

        bom_qty = sum(bom_lines.mapped('product_qty')) or 1.0
        real_weight = parent_weight * (bom_qty / (bom.product_qty or 1.0))

        _logger.info("DKGROUP: lot=%s poids intermédiaire via BOM=%s : %.3f", lot.name, bom.display_name, real_weight)

        # Si ce lot est lui-même le résultat d’une autre production, remonte récursivement
        parent_lots = lot.get_upstream_lot() - lot
        if parent_lots:
            real_weight = self._compute_weight_from_bom_recursive(parent_lots[0], real_weight)

        return real_weight


    def _compute_weight_from_bom_recursive(self, lot, parent_lot):
        """
        Recalcule le poids réel et propage le coût à partir du lot parent.
        """
        if not lot or not parent_lot:
            return 0.0

        if isinstance(lot, float) or isinstance(parent_lot, float):
            _logger.warning("DKGROUP: appel invalide _compute_weight_from_bom_recursive(lot=%s, parent=%s)", lot, parent_lot)
            return 0.0

        _logger.info("DKGROUP: [RECURSIF] lot=%s (parent=%s)", lot.name, parent_lot.name)

        production = self._get_production_from_lot(parent_lot)
        if not production:
            return parent_lot.unit_weight or 1.0

        bom = self._get_bom_for_production(production)
        if not bom:
            return parent_lot.unit_weight or 1.0

        bom_lines = bom.bom_line_ids
        if not bom_lines:
            return parent_lot.unit_weight or 1.0

        bom_qty = sum(bom_lines.mapped('product_qty')) or 1.0
        ratio = bom_qty / (bom.product_qty or 1.0)
        real_weight = (parent_lot.unit_weight or 1.0) * ratio

        lot.unit_weight = real_weight
        lot.kg_price = parent_lot.kg_price
        lot.unit_price = lot.kg_price * lot.unit_weight

        _logger.info(
            "DKGROUP: lot=%s → poids=%.3fkg, kg_price=%.3f€, unit_price=%.3f€ (parent=%s, ratio=%.3f)",
            lot.name, lot.unit_weight, lot.kg_price, lot.unit_price, parent_lot.name, ratio
        )

        # Récursion uniquement si un vrai lot parent existe
        grandparent_lots = parent_lot.get_upstream_lot() - parent_lot
        if grandparent_lots:
            _logger.info("DKGROUP: remonte à l’étape supérieure : parent=%s → grand-parent=%s", parent_lot.name, grandparent_lots[0].name)
            self._compute_weight_from_bom_recursive(parent_lot, grandparent_lots[0])

        return real_weight


    def compute_cost_price(self):

        """ return cost price and weight by lot """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for lot in self:

            lot.kg_price = 0
            lot.unit_price = 0
            lot.unit_weight = 0

            # Calcul du prix moyen pondéré
            total_cost = 0.0
            total_quantity = 0.0
            total_weight = 0.0

            # check if there is purchase
            purchase_line_ids = self.env['purchase.order.line']
            move_line_ids = self.env['stock.move.line']. search([('lot_id', '=', lot.id), ('picking_type_code', '=', 'incoming')])
            purchase_line_ids |= move_line_ids.move_id.purchase_line_id
            is_unit_price_updated = False
            
            for purchase_line in purchase_line_ids:

                if self.is_weight_based:
                    lot.unit_price = purchase_line.price_unit
                else:
                    lot.kg_price = purchase_line.price_unit

                is_unit_price_updated = True

                _logger.info(
                    "DKGROUP lot=%s (achats) -> moves=%s, pol_ids=%s, qty=%.3f, weight=%.3f, cost=%.3f",
                    lot.display_name, move_line_ids.ids, purchase_line_ids.ids,
                    total_quantity, total_weight, total_cost
                )

            check_production = True
            if is_unit_price_updated:
                check_production = False
            
            if check_production:

                parent_lots = lot.get_upstream_lot() - lot

                # 🔍 Recherche de la dernière production associée au lot parent
                parent_prods = self.env['mrp.production'].search([
                    ('move_finished_ids.move_line_ids.lot_id', 'in', parent_lots.ids)
                ], order='date_finished desc', limit=1)

                parent_lot = parent_lots[0]

                # 🔹 Fallback : si aucun prix/poids trouvé, chercher le lot parent en amont
               
                if parent_prods:
                    production = parent_prods.sorted('date_finished', reverse=True)[0]
                else:
                    production = self._get_production_from_lot(lot)

                bom = self._get_bom_for_production(production)

                _logger.info("DKGROUP -> production productionproduction: bom1 %s", str(bom))
              
                bom = self.env['mrp.bom'].search([
                        ('product_tmpl_id', '=', production.product_id.product_tmpl_id.id),
                        ('type','=','normal')
                    ], order='sequence, id', limit=1)

                _logger.info("DKGROUP -> production productionproduction: bom2 %s", str(bom))
                _logger.info("DKGROUP  production product_tmpl_id: %s", str(production.product_id.product_tmpl_id.id))
                _logger.info("DKGROUP  production bom: %s", str(bom))

                if bom:
                    # on cherche la ligne correspondant au produit du lot actuel
                    bom_line = bom.bom_line_ids

                    if bom_line:
                        # calcul du poids réel unitaire à partir de la nomenclature
                        bom_qty = bom_line.product_qty or 1.0
                        parent_weight = parent_lot.unit_weight or 1.0
                        real_unit_weight = parent_weight * (bom_qty / bom.product_qty)

                        lot.unit_weight = real_unit_weight*lot.product_qty
                        _logger.info(
                            "DKGROUP lot=%s -> poids réel recalculé via nomenclature: %.3f (parent=%.3f, ratio=%.3f)",
                            lot.name, real_unit_weight, parent_weight, bom_qty / bom.product_qty
                        )

                        # 3️⃣ Mise à jour des coûts à partir du parent
                        lot.kg_price = parent_lot.kg_price

                        if self.is_weight_based:
                            lot.kg_price = parent_lot.kg_price
                        else:
                            lot.unit_price = parent_lot.unit_price
                 
            _logger.info(
                "WARNING_DKGROUP lot=%s -> unit_weight=%.3f, unit_price=%.3f, kg_price=%.3f",
                lot.display_name, lot.unit_weight or 0.0, lot.unit_price or 0.0, lot.kg_price or 0.0
            )


