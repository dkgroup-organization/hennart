# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    _rec_name = "name"

    default_code = fields.Char('Code', related="product_id.default_code")
    weight = fields.Float("Weight", compute=False, digits='Stock Weight', store=True)
    picking_type_code = fields.Selection(related="picking_type_id.code", store=True, index=True)
    expiration_date = fields.Datetime(
        string='Expiration Date', compute=False, store=True, readonly=False, default=False,
        help='This is the date on which the goods with this Lot Number may become dangerous and must not be consumed.')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', required=True,
        compute="_compute_product_uom_id", store=True, readonly=True, precompute=True,
    )
    name = fields.Char('description', compute="compute_name", store=True)
    to_label = fields.Boolean(string='to label')
    to_weight = fields.Boolean(string='to weight')
    to_pass = fields.Boolean(string='to pass')
    to_pick = fields.Boolean(string='to pick')
    print_ok = fields.Boolean('print ok', help="This line is already labeled")
    number_of_pack = fields.Float('Nb pack', compute='compute_number_of_pack', store=True)
    quantity_per_pack = fields.Float('Quantity per pack', compute='compute_number_of_pack', store=True)
    pack_product_id = fields.Many2one('product.product', string="Pack reference",
                                      compute='compute_number_of_pack', store=True)
    priority = fields.Integer("Priority", store=True, default=0)
    production_from_id = fields.Many2one('mrp.production', related="move_id.production_id", store=True, string="Production origin")

    @api.depends('qty_done', 'move_id')
    def compute_number_of_pack(self):
        """ Count the number of pack, this is based on the stock_move and kit BOM """
        for line in self:
            number_of_pack = 0.0
            quantity_per_pack = 1.0
            pack_product_id = False
            if line.move_id.bom_line_id:
                bom = line.move_id.bom_line_id.bom_id
                pack_product_id = bom.product_id
                if bom.type == 'phantom':
                    quantity_per_pack = line.move_id.bom_line_id.product_qty
                    if quantity_per_pack:
                        number_of_pack = line.qty_done / quantity_per_pack
            line.number_of_pack = number_of_pack
            line.pack_product_id = pack_product_id
            line.quantity_per_pack = quantity_per_pack

    @api.depends('picking_id', 'product_id')
    def compute_name(self):
        """ return information about picking"""
        for line in self:
            line.name = f"({line.picking_id.name}) [{line.product_id.default_code}]{line.product_id.name}"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'expiration_date' in res:
            res['expiration_date'] = False
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ['done']:
                raise UserError(_('You can not delete product moves if the picking is done.'))

    @api.depends('product_id.uom_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.onchange('weight')
    def onchange_weight(self):
        """ valid to_weight """
        res = {}
        if self.env.context.get('manual_weight'):
            if self.qty_done <= 0.0 or self.weight <= 0.0:
                res['weight'] = 0.0
                res['to_weight'] = False
            else:
                res['to_weight'] = False
        self.update(res)

    @api.onchange('qty_done')
    def onchange_qty_done(self):
        """ define theoretical weight """
        self.ensure_one()
        res = {'weight': 0.0, 'to_weight': False}
        if self.qty_done > 0.0:
            res['weight'] = self.qty_done * self.product_id.weight
            res.update(self.get_to_weight())
        self.update(res)

    def get_to_weight(self):
        """ Check if the to_weight field has to be changed return dictionary"""
        self.ensure_one()
        res = {'to_weight': False}
        if self.product_id.uos_id == self.env['product.template']._get_weight_uom_id_from_ir_config_parameter():
            res['to_weight'] = True
        return res

    @api.onchange('lot_name', 'lot_id', 'expiration_date')
    def onchange_lot_name(self):
        """ rewrite the function to limit the check for this project
        - no serial
        - possibility to have some production lot with same name
        - don 't change qty_done
        - don't search location
        - update expiration_date
        """
        if self.lot_name and not self.lot_id:
            # create lot
            lot_vals = {'lot_name': self.lot_name,
                        'expiration_date': self.expiration_date,
                        'product_id': self.product_id.id}
            self._create_and_assign_production_lot()

        elif self.lot_name and self.lot_id:
            # update lot
            lot_vals = {'name': self.lot_name,
                        'expiration_date': self.expiration_date}
            self.lot_id.update(lot_vals)

        elif self.lot_id and not self.lot_name:
            # get lot_name
            self.update({
                'lot_name': self.lot_id.name,
                'expiration_date': self.lot_id.expiration_date,
            })
        else:
            self.update({
                'lot_name': False,
                'expiration_date': False,
                'lot_id': False
            })

    def button_test(self):
        """ Test futur function"""
        for line in self:
            # change location
            # def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
            move_data = {
                'move_line': line,
                'quantity': 1.0,
            }
            res = self.env['wms.scenario.step'].move_preparation(move_data)

    def protected_line(self):
        """ Protected line, rules to bypass the group and split operation """
        res = False
        for line in self:
            if line.picking_id.state in ['done', 'cancel'] or line.print_ok or line.qty_done != line.reserved_uom_qty \
                    or line.location_id != line.location_id.warehouse_id.wh_pack_stock_loc_id:
                res = True
                break
        return res

    def group_line(self, weighted=None):
        """ Group the line in pack if they have the same:
         pack_product_id and product_id and lot_id and location_id is preparation and quantity done and print is to do.
        """
        weighted = weighted or False
        weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        group_line = {}
        for line in self:
            if line.protected_line():
                continue
            # Exclude the product which no need weighted operation
            if weighted and line.product_id.uos_id != weight_uom:
                continue

            pack_key = f'{line.move_id.id}-{line.product_id.id}-{line.pack_product_id.id or 0}-{line.lot_id.id or 0}'
            if pack_key not in list(group_line.keys()):
                group_line[pack_key] = line
            else:
                group_line[pack_key] |= line

        for line_ids in group_line.values():
            if len(line_ids) == 1:
                # No need grouping if only one line
                continue

            qty_done = sum(line_ids.mapped('qty_done'))
            weight = sum(line_ids.mapped('weight'))
            to_weight = any(line_ids.mapped('to_weight'))
            to_label = any(line_ids.mapped('to_label'))
            reserved_uom_qty = sum(line_ids.mapped('reserved_uom_qty'))

            line_to_write = line_ids[0]
            unlink_move_line = line_ids - line_to_write
            unlink_move_line.unlink()

            line_to_write.reserved_uom_qty = reserved_uom_qty > 0.0 and reserved_uom_qty or 0.0
            line_to_write.qty_done = qty_done
            line_to_write.weight = weight
            line_to_write.to_weight = to_weight
            line_to_write.to_label = to_label

    def split_by_pack(self):
        """ Split this line by pack to weight, create new line with 1 pack per line if unit of sale is weight """
        weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for line in self:
            if line.protected_line():
                continue

            if line.product_id.uos_id == weight_uom:
                if line.number_of_pack > 1.0:
                    pack_weight = line.product_id.weight * line.number_of_pack
                    quantity_per_pack = line.quantity_per_pack
                    priority = line.priority
                else:
                    pack_weight = line.product_id.weight
                    quantity_per_pack = line.quantity_per_pack or 1.0
                    priority = line.priority

                while line.qty_done > quantity_per_pack:
                    line.qty_done -= quantity_per_pack
                    line.reserved_uom_qty -= quantity_per_pack
                    if line.reserved_uom_qty < 0.0:
                        line.reserved_uom_qty = 0.0
                    line.weight -= pack_weight
                    if line.weight < 0.0:
                        line.weight = 0.0
                    line_vals = {
                        'qty_done': quantity_per_pack,
                        'reserved_uom_qty': quantity_per_pack,
                        'weight': pack_weight,
                        'to_weight': True,
                        'priority': priority,
                    }
                    line.copy(line_vals)
                line.to_weight = True

    def put_to_label(self):
        """ Check if the line is to label """
        # label_type in ['no_label', 'weight_label', 'lot_label', 'pack_label', 'product_label'],
        for line in self:
            label_type = line.picking_id.label_type
            if label_type == 'no_label' or line.protected_line():
                line.to_label = False
            elif (line.product_id.to_label or line.pack_product_id.to_label) and label_type in ['product_label', 'weight_label']:
                line.to_label = True
            elif label_type == 'weight_label':
                line.to_label = line.to_weight
            elif label_type in ['lot_label', 'pack_label', 'product_label']:
                line.to_label = True
            else:
                line.to_label = False

    def print_label(self, printer=None, label_id=None):
        """ Print label, future function """
        pass
