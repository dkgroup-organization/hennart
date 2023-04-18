from odoo import fields, models, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError


class HistoryLines(models.Model):
    _name = "cadence.history.lines"
    _description = "History Lines"

    product_id = fields.Many2one('product.product', string="Article", required=True)

    qty = fields.Float(string='Qty')
    discount = fields.Float(string='Promo %')

    weight = fields.Float('Poids', compute="compute_uos_qty", readonly=True)

    availability = fields.Char(string='Dispo.', compute='_compute_availability', readonly=True)

    cadence = fields.Html(string="Cadencier", readonly=True)

    sale_order_id = fields.Many2one('sale.order', string='Order', index=True)

    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line', index=True)

    @api.depends('qty', 'product_id.qty_available')
    def _compute_availability(self):
        for line in self:
            qty_available = line.product_id.qty_available
            if line.qty > qty_available:
                line.availability = '<span class="text-danger fa fa-times"></span>' + str(qty_available)
            else:
                line.availability = '<span class="text-success fa fa-check"></span>' + str(qty_available)

    @api.depends('product_id', 'qty')
    def compute_uos_qty(self):
        """ compute the value of weight"""
        for line in self:
            if line.product_id:
                line.weight = line.product_id.weight * line.qty
            else:
                line.weight = 0

    @api.onchange('qty', 'discount')
    def _onchange_qty_or_discount(self):
        if self.sale_order_id:
            if self.sale_order_id._origin: # Vérifier s'il y a une commande parente existante
                sale_order_id = self.sale_order_id._origin.id
            else: # sinon utiliser l'ID de la commande parente actuelle
                sale_order_id = self.sale_order_id.id
                
            sale_order_line = self.env['sale.order.line'].search([
                ('order_id', '=', sale_order_id),
                ('product_id', '=', self.product_id.id),
            ], limit=1)
            if not sale_order_line:
                sale_order_line = self.env['sale.order.line'].create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': self.qty,
                    'discount': self.discount,
                    'order_id': sale_order_id,
                })
            else:
                sale_order_line.write({
                    'product_uom_qty': self.qty,
                    'discount': self.discount,
                })
            # Sauvegarder manuellement la commande parente
            self.sale_order_id.write({})
            self.sale_order_line_id.write({})
            self.write({})
            # Mise à jour de l'interface utilisateur
            self.update_sale_order_line_ui(sale_order_line.id)

            # sale_order_line.recompute()

    def update_sale_order_line_ui(self, sale_order_line_id):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }