# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    _rec_name = "name"

    default_code = fields.Char('Code', related="product_id.default_code")
    weight = fields.Float("Weight", compute=False, digits='Stock Weight', store=True)
    picking_type_code = fields.Selection('Type', related="picking_type_id.code", store=True, index=True)
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
    priority = fields.Integer("Priority", store=True, default=0)

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
        res = {'weight': 0.0, 'to_weight': False}
        if self.qty_done > 0.0:
            res['weight'] = self.qty_done * self.product_id.weight
            if self.product_id.uos_id == self.env['product.template']._get_weight_uom_id_from_ir_config_parameter():
                res['to_weight'] = True
            else:
                res['to_weight'] = False
        self.update(res)

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

