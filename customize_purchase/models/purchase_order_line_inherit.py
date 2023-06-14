# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'



    discount1 = fields.Float("R1 %",compute="get_price",store=True)
    discount2 = fields.Float("R2 %",compute="get_price",store=True)
    base_price = fields.Float("Base price",compute="get_price",store=True)
    discount = fields.Float(string="Discount (%)", editable=True)
    product_uos = fields.Many2one("uom.uom",string="Invoicing unit",readonly=True,compute="get_price",store=True)
    max_qty = fields.Float('Stock',compute="_get_stock")
    weight = fields.Float('Unit Weight',compute="get_price",store=True)
    total_weight = fields.Float('Weight',compute="get_price",store=True)
    #product_packaging_id = fields.Many2one(domain=_get_product_packaging_domain)

    @api.depends('product_id')
    def _get_stock(self):
        for rec in self:
            rec.max_qty = rec.product_id.qty_available

    _sql_constraints = [('maximum_discount','CHECK (discount<=100)','Discount must be lower than 100%.',)]


    ## part of discount managements
    @api.onchange('product_id')
    def calculate_discount_percentage(self):
        if(self.order_id.date_order):
            vendor = self.order_id.partner_id
            planned_date = self.order_id.date_order.date()
            for line in self:
                if line.order_id.state not in ['draft', 'sent'] or not line.product_id:
                    continue
                promotions = self.env['purchase.promotion'].search([('product_id', '=', line.product_id.id),
                                                                    ('supplier_id', '=', vendor.id),
                                                                    ('date_start', '<=', planned_date),
                                                                    ('date_end', '>=', planned_date)])
                if promotions.discount:
                    line.write({'discount': promotions.discount})

                else:
                    line.write({'discount': 0.0})



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

    # def _prepare_account_move_line(self, move=False):
    #     rec = super(PurchaseOrderLineInherit, self)._prepare_account_move_line(move=False)
    #     rec.update({'discount': self.discount,'discount1': self.discount1,
    #                 'discount2': self.discount2,'base_price': self.base_price,'weight': self.weight,
    #                 'product_uos': self.product_uos.id,'product_packaging_id': self.product_packaging_id.id,
    #                 'product_packaging_qty': self.product_packaging_qty})
    #     return rec



    ## end part of discount management


    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super(PurchaseOrderLineInherit, self)._prepare_purchase_order_line(product_id,product_qty,product_uom,company_id,supplier,po)
        discount1 = supplier.discount1
        discount2 = supplier.discount2
        base_price = supplier.base_price
        res.update(
            discount1=discount1,
            discount2=discount2,
            base_price=base_price)
        return res


    @api.depends('product_id','product_qty')
    def get_price(self):
        for line in self:
            if line.order_id.state not in ['draft', 'sent'] or not line.product_id:
                continue
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=line.product_uom,)
            if (seller):
                line.discount1 = seller.discount1
                line.discount2 = seller.discount2
                line.base_price = seller.base_price
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


    @api.depends('product_id', 'product_qty', 'product_uom')
    def _compute_product_packaging_id(self):
        for line in self:
            # remove packaging if not match the product
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            # suggest biggest suitable packaging
            if line.product_id and line.product_qty and line.product_uom:
                seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=line.product_uom,)
                if(seller and seller.packaging):
                    line.product_packaging_id = seller.packaging
                else:
                    line.product_packaging_id = line.product_id.packaging_ids.filtered('purchase')._find_suitable_product_packaging(line.product_qty, line.product_uom) or line.product_packaging_id