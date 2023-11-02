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

    def get_theoric_weight(self):
        """ return theoretical weight to qweb"""
        weight = 0
        nb_lines = 0
        for picking in self:
            nb_lines += len(picking.move_ids_without_package)
            for move in picking.move_ids_without_package:
                weight += move.product_uom_qty * move.product_id.weight

        res = str(nb_lines) + _(" lines, ") + str(int(weight)) + " Kg"
        return res

    @api.depends('scheduled_date')
    def _compute_sequence(self):
        for picking in self:
            dt = picking.scheduled_date or fields.Datetime.now()
            # (2000 - dt.year) * 10000
            date_score = dt.month * 100 + dt.day
            weight_score = int(sum(move.product_uom_qty * move.product_id.weight for move in picking.move_ids_without_package))

            # Adaptez les coefficients, TODO: add carrier and disponibility priority
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
        self.move_ids_without_package.move_line_ids.filtered(lambda x: x.qty_done == 0.0).unlink()
        res = super().button_validate()
        canceled_move = self.move_ids_without_package.filtered(lambda x: x.state == 'cancel')
        canceled_move.sudo().move_line_ids.unlink()
        return res

    def order_move_line(self):
        """ Order the move line priority"""
        for picking in self:
            # the order is defined by location
            moves_line_ids = self.env['stock.move.line'].search([
                ('picking_id', '=', picking.id)
                ])

            moves_line_ids = sorted(moves_line_ids, key=lambda ml: ml.location_id.complete_name)

            priority = 100
            for move_line in moves_line_ids:
                move_line.priority = priority
                priority += 10

    def action_assign(self):
        """ order stock.move.line by location name"""
        res = super().action_assign()
        self.order_move_line()
        return res
