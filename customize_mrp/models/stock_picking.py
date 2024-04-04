# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_mrp(self):
        """ Check if all product with BOM need manufacture, recursive analyse """
        product_todo = {}

        for picking in self:
            if picking.state in ['cancel', 'done']:
                continue
            for move in picking.move_ids_without_package:
                if move.product_id.bom_ids:
                    if move.product_id.id not in list(product_todo.keys()):
                        product_todo[move.product_id.id] = 0.0

        def explode_product(product_todo):
            """ List all product in BOM """
            new_product_todo = {}
            for product_id in list(product_todo.keys()):
                product = self.env['product.product'].browse(product_id)
                bom = product.bom_ids and product.bom_ids[0] or self.env['mrp.bom']

                if bom:
                    for line in bom.bom_line_ids:
                        if line.product_id.bom_ids:
                            if line.product_id.id not in list(new_product_todo.keys()):
                                new_product_todo[line.product_id.id] = 0.0

            result_product_todo = {}
            if new_product_todo:
                result_product_todo = explode_product(new_product_todo)
            result_product_todo.update(product_todo)
            return result_product_todo

        product_todo = explode_product(product_todo)
        product_ids = self.env['product.product'].browse(list(product_todo.keys()))
        production_ids = product_ids.action_mrp()

        for production in production_ids:
            move_ids = self.env['stock.move'].search([('picking_id', 'in', self.ids),
                                                      ('product_id', '=', production.product_id.id)])
            move_ids.group_id = production.procurement_group_id
        return True

