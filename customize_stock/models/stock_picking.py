# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    #date_delivered = fields.Datetime("delivered date", compute='compute_date_delivered', help="Customer delivered date")
    picking_type_code = fields.Selection(string='Code', related="picking_type_id.code")
    sequence = fields.Integer(string='Sequence', compute='_compute_sequence', store=True)

    @api.depends('scheduled_date', 'move_ids_without_package', 'move_ids_without_package.product_uom_qty')
    def _compute_sequence(self):
        for picking in self:
            dt = picking.scheduled_date or fields.Datetime.now()
            date_score = (2000 - dt.year) * 10000 + dt.month * 100 + dt.day
            weight_score = int(sum(move.product_uom_qty * move.product_id.weight for move in picking.move_ids_without_package))

            # Adaptez les coefficients comme nécessaire
            picking.sequence = int(date_score * 10000 + weight_score)

    def compute_date_delivered(self):
        """ Custom delivery, Always delivery at one time with no backorder"""
        for picking in self:
            if picking.state in ['done', 'cancel']:
                continue
            if not picking.date_delivered:
                picking.date_delivered = fields.Datetime.now()

    def button_validate(self):
        """ Add some checking before validation """
        self.move_ids_without_package.check_line()
        return super().button_validate()

    @api.model
    def get_user_picking(self):
        """ return the set of picking currently in preparation by this user"""
        picking_type = self.env.ref('stock.picking_type_out')

        picking_ids = self.env['stock.picking'].search([
            ('user_id', '=', self.env.user.id),
            ('picking_type_id', '=', picking_type.id),
            ('state', 'in', ['assigned', 'confirmed', 'waiting'])
        ], order='sequence')

        return picking_ids

    @api.model
    def add_next_picking(self):
        """ assign next picking to this user"""
        picking_type = self.env.ref('stock.picking_type_out')

        picking_ids = self.env['stock.picking'].search([
            ('user_id', '=', False),
            ('picking_type_id', '=', picking_type.id),
            ('state', 'in', ['assigned'])
        ], order='sequence', limit=1)
        if picking_ids:
            picking_ids.user_id = self.env.user

        return self.get_user_picking()
