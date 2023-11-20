# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging
from odoo.fields import Command
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    default_code = fields.Char('Code', related="product_id.default_code")
    product_packaging_qty = fields.Float('Packaging Quantity')
    weight = fields.Float(
        string="Weight",
        compute='get_weight',
        inverse="put_weight", readonly=False,
        store=True, precompute=False,
        digits='Stock Weight',
    )
    quantity_done = fields.Float(
        string="Done",
        compute='get_quantity_done',
        inverse="put_quantity_done", readonly=False,
        store=True, precompute=False,
        digits='Product Unit of Measure',
    )
    prodlot_inv = fields.Char(
        string="Supplier N° lot",
        compute='get_prodlot_inv',
        inverse="put_prodlot_inv", readonly=False,
        store=False, precompute=False,
    )
    lot_expiration_date = fields.Date(
        string='Expiration Date',
        compute='get_prodlot_inv',
        inverse="put_prodlot_inv", readonly=False,
        store=False, precompute=False,
        help='This is the date on which the goods with this Serial Number may'
                ' become dangerous and must not be consumed.')

    picking_type_use_create_lots = fields.Boolean(related='picking_type_id.use_create_lots', readonly=True)
    lot_description = fields.Text("Lot description", compute="get_lot_description", store=False,
                                  readonly=True, sanitize=False)
    
    mrp_id = fields.Many2one(
        'mrp.production',
        string='mrp',
        )

    wh_filter = fields.Boolean('In/Out move', compute="get_wh_in_out", store=True, index=True)

    @api.depends('location_id', 'location_dest_id', 'state', 'product_qty', 'product_id')
    def get_wh_in_out(self):
        """ filter the move to use in report quantity and prevision"""
        for move in self:
            if move.state in ['cancel', 'draft', 'done']:
                move.wh_filter = False
            elif move.product_id.product_tmpl_id.type != 'product':
                move.wh_filter = False
            elif move.product_qty == 0.0:
                move.wh_filter = False
            elif move.location_id.usage in ['internal', 'transit'] or \
                    move.location_dest_id.usage in ['internal', 'transit']:
                if move.location_id.warehouse_id != move.location_dest_id.warehouse_id:
                    move.wh_filter = True
                else:
                    move.wh_filter = False
            else:
                move.wh_filter = False




    def check_line(self):
        """ check if all line has production lot information"""
        message = ""
        for move in self:
            for move_line in move.move_line_ids:
                if move_line.state == "cancel":
                    continue
                if not move_line.qty_done:
                    continue
                if move_line.lot_id and not move_line.lot_id.expiration_date:
                    message += _(f"\nThis lot need a expiration date: {move.name} {move_line.lot_id.name}")
                if (move_line.weight == 0.0 or move_line.to_weight) and move_line.qty_done > 0.0:
                    message += _(f"\nThis line need a weight: {move.name}")

        if message:
            raise ValidationError(message)

    def get_default_value(self, vals={}):
        self.ensure_one()
        vals.update(
            {
                'picking_id': self.picking_id.id,
                'move_id': self.id,
                'company_id': self.company_id.id,
                'product_id': self.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_id': self.product_uom.id,
            })
        return vals

    @api.depends('move_line_ids.lot_id')
    def get_prodlot_inv(self):
        """ Get prodlot_inv"""
        for line in self:
            if len(line.move_line_ids) == 1:
                lot = line.move_line_ids.lot_id
                if lot:
                    line.prodlot_inv = lot.name
                    line.lot_expiration_date = lot.expiration_date
                else:
                    line.prodlot_inv = ''
                    line.lot_expiration_date = False
            else:
                line.prodlot_inv = ''
                line.lot_expiration_date = False

    def put_prodlot_inv(self):
        """ Create move_line_ids to save value"""
        for line in self:
            if not line.prodlot_inv or not line.lot_expiration_date:
                continue
            elif not line.move_line_ids:
                move_line_vals = line.get_default_value(
                    {'lot_name': line.prodlot_inv,
                     'expiration_date': line.lot_expiration_date})
                line.move_line_ids.create(move_line_vals)
                line.move_line_ids._create_and_assign_production_lot()
            elif len(line.move_line_ids) == 1:
                if not line.move_line_ids.lot_id:
                    line.move_line_ids.update(
                        {'lot_name': line.prodlot_inv,
                         'expiration_date': line.lot_expiration_date})
                    line.move_line_ids._create_and_assign_production_lot()
                else:
                    line.move_line_ids.update(
                        {'lot_name': line.prodlot_inv,
                         'expiration_date': line.lot_expiration_date})
                    line.move_line_ids.lot_id.update({'name': line.prodlot_inv,
                                                      'expiration_date': line.lot_expiration_date})
            else:
                message = _("this line has multiples production lot, uses the detailed view to update")
                message += '\n {}'.format(line.name)
                raise ValidationError(message)

    @api.depends('move_line_ids.qty_done')
    def get_quantity_done(self):
        """ Get quantity_done"""
        for line in self:
            if line.state == 'done':
                continue

            quantity_done = 0.0
            if line.state != 'cancel':
                for stock_move_line in line.move_line_ids:
                    quantity_done += stock_move_line.qty_done
            line.quantity_done = quantity_done

    def put_quantity_done(self):
        """ Create move_line_ids to save value"""
        for line in self:
            move_line_vals = line.get_default_value({'qty_done': line.quantity_done})
            if line.product_id.uos_id == self.env['product.template']._get_weight_uom_id_from_ir_config_parameter():
                move_line_vals['to_weight'] = True
            move_line_vals['weight'] = line.product_id.weight * line.quantity_done

            if not line.move_line_ids:
                line.move_line_ids.create(move_line_vals)
            elif len(line.move_line_ids) == 1:
                line.move_line_ids.update(move_line_vals)
            else:
                message = _("this line has multiples production lot, uses the detailed view to update")
                message += '\n {}'.format(line.name)
                raise ValidationError(message)

    @api.depends('move_line_ids.weight')
    def get_weight(self):
        """ Get weight"""
        for line in self:
            if line.state == 'done':
                continue

            weight = 0.0
            if line.state != 'cancel':
                for stock_move_line in line.move_line_ids:
                    weight += stock_move_line.weight
            line.weight = weight

    def put_weight(self):
        """ Create move_line_ids to save value"""
        for line in self:
            move_line_vals = line.get_default_value({'weight': line.weight})
            move_line_vals['to_weight'] = False

            if not line.move_line_ids:
                line.move_line_ids.create(move_line_vals)
            elif len(line.move_line_ids) == 1:
                line.move_line_ids.update(move_line_vals)
            else:
                message = _("this line has multiples production lot, uses the detailed view to update")
                message += '\n {}'.format(line.name)
                raise ValidationError(message)

    @api.depends('move_line_ids.lot_id')
    def get_lot_description(self):
        """ Get lot description"""
        for move in self:
            lot_description = ""
            lots = {}
            for move_line in move.move_line_ids:
                if move_line.lot_id and move_line.lot_id not in lots:
                    lots[move_line.lot_id] = move_line.qty_done
                elif move_line.lot_id:
                    lots[move_line.lot_id] += move_line.qty_done

            for lot in lots:
                lot_description += "{}".format(lot.ref or '?')
                if lot.expiration_date:
                    lot_description += " {:%d/%m/%Y}".format(lot.expiration_date)
                lot_description += "({})".format(lots[lot])
                lot_description += ", "

            move.lot_description = lot_description

    def write(self, vals):
        """ By pass quantity_done constraint
        put zero quantity and weight on cancel move
        """
        if 'state' in vals and vals['state'] == 'cancel':
            for move in self:
                if move.state != 'cancel':
                    move.move_line_ids.write({'qty_done': 0.0, 'weight': 0.0})
        if 'quantity_done' in vals and any(move.state == 'cancel' for move in self):
            del vals['quantity_done']
        return super().write(vals)

    def _do_unreserve(self):
        """ Don't unreserve the product on preparation location, it's too late, the products are moving"""
        super()._do_unreserve()
        location_preparation_ids = self.env['stock.warehouse'].search([]).mapped('wh_pack_stock_loc_id')
        # Do not unreserved preparation location
        move_line_ids = self.env['stock.move.line'].search([
            ('location_id', 'in', location_preparation_ids.ids),
            ('move_id', 'in', self.ids),
            ])
        moves_to_recompute = self.env['stock.move']
        for move_line in move_line_ids:
            if move_line.reserved_uom_qty != move_line.qty_done:
                move_line.reserved_uom_qty = move_line.qty_done
                moves_to_recompute |= move_line.move_id
        moves_to_recompute._recompute_state()

        for move in moves_to_recompute:
            quant_ids = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('location_id', 'in', location_preparation_ids.ids)
            ])
            for quant in quant_ids:
                if quant.reserved_quantity != quant.quantity:
                    quant.reserved_quantity = quant.quantity

        return True
