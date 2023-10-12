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
