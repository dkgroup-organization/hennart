# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging
from odoo.fields import Command
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

    def check_line(self):
        """ check if all line has production lot information"""
        message = ""
        for move in self:
            for move_line in move.move_line_ids:
                if move_line.state == "cancel":
                    continue
                if move_line.weight == 0.0 and move_line.qty_done == 0.0:
                    move_line.unlink()
                    continue
                if move_line.lot_id and not move_line.lot_id.expiration_date:
                    message += _(f"\nThis lot need a expiration date: {move.name} {move_line.lot_id.name}")
                if move_line.weight == 0.0 and move_line.qty_done > 0.0:
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
            if line.state in ['cancel', 'done']:
                continue

            quantity_done = 0.0
            for stock_move_line in line.move_line_ids:
                quantity_done += stock_move_line.qty_done
            line.quantity_done = quantity_done

    def put_quantity_done(self):
        """ Create move_line_ids to save value"""
        for line in self:
            move_line_vals = line.get_default_value({'qty_done': line.quantity_done})

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
            if line.state in ['cancel', 'done']:
                continue

            weight = 0.0
            for stock_move_line in line.move_line_ids:
                weight += stock_move_line.weight
            line.weight = weight

    def put_weight(self):
        """ Create move_line_ids to save value"""
        for line in self:
            move_line_vals = line.get_default_value({'weight': line.weight})

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
            for move_line in move.move_line_ids:
                if move_line.lot_id:
                    lot_description += "{}".format(move_line.lot_id.ref or '?')
                    if move_line.lot_id.expiration_date:
                        lot_description += " {:%d/%m/%Y}".format(move_line.lot_id.expiration_date)
                    if move_line.qty_done != move.quantity_done:
                        lot_description += "({})".format(move_line.qty_done)
                    lot_description += ", "
            move.lot_description = lot_description

