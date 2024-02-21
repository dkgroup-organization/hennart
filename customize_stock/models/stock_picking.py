# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date_delivered = fields.Datetime("delivered date", help="Customer delivered date")
    picking_type_code = fields.Selection(string='Code', related="picking_type_id.code")
    sequence = fields.Integer(string='Sequence', compute='_compute_sequence', store=True)
    preparation_state = fields.Selection([
        ('wait', 'wait'), ('pick', 'pick'), ('weight', 'weight'), ('label', 'label'),
        ('ready', 'ready'), ('done', 'done')],
        string='Preparation', compute="compute_preparation_state", default='wait')

    label_type = fields.Selection(
        [('no_label', 'No label'), ('weight_label', 'Label all weighted'), ('lot_label', 'Label all lots'),
         ('pack_label', 'Label all packs'), ('product_label', 'Label all products')],
        default="lot_label", string="Label strategy")

    def compute_preparation_state(self):
        """ Compute preparation state """
        for picking in self:
            preparation_state = ''
            if picking.state in ['done', 'cancel']:
                preparation_state = 'done'
            elif picking.state == 'draft' or not picking.move_line_ids:
                preparation_state = 'wait'
            else:
                for move_line in picking.move_line_ids:
                    if move_line.qty_done < move_line.reserved_uom_qty:
                        preparation_state = 'pick'
                        break

                if not preparation_state:
                    for move_line in picking.move_line_ids:
                        if move_line.to_weight:
                            preparation_state = 'weight'
                            break

                if not preparation_state:
                    for move_line in picking.move_line_ids:
                        if move_line.to_label:
                            preparation_state = 'label'
                            break

                if not preparation_state:
                    for move in picking.move_ids_without_package:
                        if move.product_uom_qty > move.quantity_done:
                            preparation_state = 'wait'
                            break

                if not preparation_state:
                    preparation_state = 'ready'

            picking.preparation_state = preparation_state

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

            # Adaptez les coefficients, TODO: add carrier and disponibility priority hour
            picking.sequence = int(date_score * 10000 + weight_score)

    def compute_date_delivered(self):
        """ Custom delivery, Always delivery at one time with no backorder """
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
            moves_line_ids = self.env['stock.move.line'].search([('picking_id', '=', picking.id)])
            moves_line_ids = sorted(moves_line_ids, key=lambda ml: ml.location_id.complete_name)

            priority = 1000
            for move_line in moves_line_ids:
                move_line.priority = priority
                priority += 1000

    def action_mrp(self):
        for picking in self:
            for move in picking.move_ids_without_package:
                product = move.product_id
                min_production_qty = product.min_production_qty
                quantity_to_produce = move.product_uom_qty

                if move.product_id.bom_ids != False:
                    if move.product_uom_qty != move.forecast_availability and move.product_uom_qty > 0:
                        if move.mrp_id == False:

                            in_process_productions = self.env['mrp.production'].search([
                                ('product_id', '=', product.id),
                                ('state', '=', 'draft'),
                                ])
                            
                            if quantity_to_produce <= min_production_qty:
                                quantity_to_produce = min_production_qty

                            elif quantity_to_produce % min_production_qty != 0:
                                quantity_to_produce = (min_production_qty * ((quantity_to_produce // min_production_qty) + 1)) - move.forecast_availability

                        # if move_line.state == 'assigned' and move_line.product_uom_qty > 0:

                            if in_process_productions:
                                quantity = in_process_productions.product_qty + quantity_to_produce
                                in_process_productions.write({
                                    'product_qty': quantity,
                                    'move_from_picking_ids': [(4, move.id)],  
                                    })
                                
                            else:
                                production_order = self.env['mrp.production'].create({
                                    'product_id': move.product_id.id,
                                    'product_qty': quantity_to_produce,
                                    'move_from_picking_ids': [(4, move.id)],  

                                })

                            # production_order.action_confirm()  # Confirmer le MO
                            # production_order.button_plan()  # Planifier le MO
                            # production_order.action_produce()  # Démarrer la production du MO

    def action_assign(self):
        """ order stock.move.line by location name"""
        res = super().action_assign()
        self.order_move_line()
        return res

    def compute_number_of_pack(self):
        """ compute number of pack on each line """
        self.move_line_ids.compute_number_of_pack()

    def split_by_pack(self):
        """ Split the line by pack if the unit of sale is weight, in this case the line is to weight  """
        self.move_line_ids.split_by_pack()

    def group_line(self):
        """ Group the line by lot and product  """
        for picking in self:
            picking.move_line_ids.group_line()

    def label_preparation(self):
        """ Choice action to label
        label_type in ['no_label', 'weight_label', 'lot_label', 'pack_label', 'product_label'],
        """
        for picking in self:
            partner = picking.partner_id.parent_id or picking.partner_id

            if not partner:
                picking.label_nothing()
            elif partner.label_forced:
                picking.label_all_pack()
            elif partner.label_all_product:
                picking.label_all_product()
            elif partner.label_needed:
                picking.label_all_weighted()
            else:
                picking.label_nothing()

    def label_nothing(self):
        """ Label nothing """
        for picking in self:
            picking.label_type = 'no_label'
            picking.move_line_ids.put_to_label()

    def label_all_pack(self):
        """ Label all pack, create and weight all pack, no exception """
        for picking in self:
            picking.label_type = 'pack_label'
            picking.move_line_ids.group_line()
            picking.move_line_ids.split_by_pack()
            picking.move_line_ids.put_to_label()

    def label_all_weighted(self):
        """ Label only the product which need a new weighted """
        for picking in self:
            picking.label_type = 'weight_label'
            picking.move_line_ids.group_line(weighted=True)
            picking.move_line_ids.put_to_label()

    def label_all_product(self):
        """ All product need a label """
        for picking in self:
            picking.label_type = 'product_label'
            picking.move_line_ids.group_line()
            picking.move_line_ids.put_to_label()

    def label_all_lot(self):
        """ all lot need a label, one is enough by lot """
        for picking in self:
            picking.label_type = 'lot_label'
            picking.move_line_ids.group_line()
            picking.move_line_ids.put_to_label()
