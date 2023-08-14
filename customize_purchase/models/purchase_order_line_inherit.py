# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    supplier_discount_type = fields.Selection(string="Type of supplier info",selection=[('discount','Cascade discount'),('add','Add discount')],default="discount")
    discount1 = fields.Float("R1 %", compute="get_price", store=True)
    discount2 = fields.Float("R2 %", compute="get_price", store=True)
    base_price = fields.Float("Base price", compute="get_price", store=True)
    discount = fields.Float(string="Discount (%)", compute="calculate_discount_percentage", store=True)
    product_uos = fields.Many2one("uom.uom", string="Unit", compute="get_price", store=True)
    max_qty = fields.Float('Stock', compute="_get_stock")
    weight = fields.Float('Unit Weight', compute="get_price", store=True)
    total_weight = fields.Float('Weight', compute="get_price", store=True)
    default_code = fields.Char("code", related="product_id.default_code", store=True)
    weight_picking = fields.Float(compute='_compute_weight_picking', string='Weight received', store=True,
                                  readonly=True)

    date_planned = fields.Datetime(string='Warehouse date', compute="_compute_date_planned", store=True, index=True)

    product_packaging_id = fields.Many2one('product.packaging', string='Packaging',
                                           domain="[('purchase', '=', True), ('product_id', '=', product_id)]",
                                           compute="_compute_product_packaging", store=True)
    product_packaging_qty = fields.Float('Packaging Quantity', compute="_compute_product_packaging", store=True)

    @api.depends('order_id.date_planned')
    def _compute_date_planned(self):
        """ Not used"""
        for line in self:
            line.date_planned = line.order_id.date_planned

    @api.depends('move_ids.weight')
    def _compute_weight_picking(self):
        for line in self:
            weight = 0.0
            for move_line in line.move_ids:
                weight += move_line.weight
            line.weight_picking = weight

    def _prepare_account_move_line(self, move=False):
        rec = super(PurchaseOrderLineInherit, self)._prepare_account_move_line(move=False)
        rec.update({'weight': self.weight_picking,'prodlot_id': [(6, 0, self.move_ids.mapped('lot_ids').ids)]})
        return rec


    @api.depends('product_id')
    def _get_stock(self):
        for rec in self:
            rec.max_qty = rec.product_id.qty_available

    _sql_constraints = [('maximum_discount','CHECK (discount<=100)','Discount must be lower than 100%.',)]

    ## part of discount managements
    @api.depends('product_id', 'date_planned', 'partner_id')
    def calculate_discount_percentage(self):
        for line in self:
            vendor = line.partner_id
            date_planned = line.order_id.date_planned

            if date_planned:
                if line.order_id.state not in ['draft', 'sent'] or not line.product_id or not date_planned:

                    continue
                condition = [('product_id', '=', line.product_id.id), ('supplier_id', '=', vendor.id),
                             ('date_start', '<=', date_planned.date()), ('date_end', '>=', date_planned.date())]

                promotions = self.env['purchase.promotion'].search(condition)

                if promotions.discount:
                    line.discount = promotions.discount
                else:
                    line.discount = 0.0
            else:
                line.discount = 0.0

    @api.depends("discount","weight")
    def _compute_amount(self):
        return super()._compute_amount()

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        quantity = self.product_qty
        subtotal = self.price_subtotal
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if(self.product_uos.id == uom_weight.id):
            quantity = self.weight * self.product_qty
        if self.discount:
            line_discount_price_unit = self.price_unit * (1 - (self.discount / 100.0))
            subtotal = quantity * line_discount_price_unit
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=quantity,
            discount=self.discount,
            price_subtotal=subtotal,
        )

    def _prepare_account_move_line(self, move=False):
        rec = super(PurchaseOrderLineInherit, self)._prepare_account_move_line(move=False)
        data = {'discount': self.discount, 'discount1': self.discount1,
                    'discount2': self.discount2, 'initial_price': self.base_price,
                    'product_uos': self.product_uos.id or self.product_uom_id.id,'supplier_discount_type':self.supplier_discount_type}

        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        quantity = self.product_qty
        if (self.product_uos.id == uom_weight.id):
            quantity = self.weight * self.product_qty
            data.update({'quantity' : quantity})
        rec.update(data)


        return rec

    ## end part of discount management
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super(PurchaseOrderLineInherit, self)._prepare_purchase_order_line(product_id,product_qty,product_uom,company_id,supplier,po)
        discount1 = supplier.discount1
        discount2 = supplier.discount2
        base_price = supplier.base_price
        supplier_discount_type = supplier.type
        res.update(
            discount1=discount1,
            discount2=discount2,
            base_price=base_price,
            supplier_discount_type = supplier_discount_type,
        )
        return res

    @api.depends('product_id', 'product_qty', 'order_id.date_planned')
    def get_price(self):
        for line in self:

            if line.order_id.state not in ['draft', 'sent'] or not line.product_id:
                continue
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_planned and line.order_id.date_planned.date(),
                uom_id=line.product_uom,)
            if (seller):
                line.discount1 = seller.discount1
                line.discount2 = seller.discount2
                line.base_price = seller.base_price
                line.supplier_discount_type = seller.type
                if (seller.product_name):
                    line.name = seller.product_name
                if (seller.product_uos):
                    line.product_uos =seller.product_uos
                else:
                    line.product_uos = line.product_id.uom_po_id
            else:
                line.discount1 = line.discount2 = line.base_price = 0.0
                line.product_uos = line.product_id.uom_po_id
            weight = line.product_id.weight
            line.weight = weight
            line.total_weight = weight * line.product_qty

    @api.depends('product_id', 'partner_id', 'product_qty', 'product_uom', 'order_id.date_planned')
    def _compute_product_packaging(self):
        for line in self:
            if line.order_id.date_planned:
                date_planned = line.order_id.date_planned.date() or fields.Datetime.now().date()

            # suggest biggest suitable packaging
            if line.product_id and line.product_qty and line.product_uom and line.partner_id:
                seller = line.product_id._select_seller(
                                partner_id=line.partner_id,
                                quantity=line.product_qty,
                                date=date_planned,
                                uom_id=line.product_uom,)
                if seller:
                    line.product_packaging_id = seller.packaging

            # remove packaging if not match the product
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False

            if not line.product_packaging_id:
                line.product_packaging_qty = 0
            else:
                packaging_uom = line.product_id.uom_id
                packaging_uom_qty = line.product_qty
                product_packaging_qty = float_round(packaging_uom_qty / line.product_packaging_id.qty,
                                                    precision_rounding=packaging_uom.rounding)
                if product_packaging_qty - float(int(product_packaging_qty)) > packaging_uom.rounding:
                    product_packaging_qty += 1.0

                line.product_packaging_qty = float(int(product_packaging_qty))
                line.product_qty = line.product_packaging_qty * line.product_packaging_id.qty

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        values = super(PurchaseOrderLineInherit,self)._prepare_stock_move_vals(picking,price_unit,product_uom_qty,product_uom)
        values['product_packaging_qty'] = self.product_packaging_qty
        values['date'] = self.order_id.date_planned
        values['date_deadline'] =  self.order_id.date_planned
        return values


