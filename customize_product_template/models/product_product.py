# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.tools.float_utils import float_round, float_is_zero


class ProductProduct(models.Model):
    _inherit = 'product.product'
    _order = 'name, default_code'

    base_product_id = fields.Many2one("product.product", string="base product",
                                        compute="compute_base_product", store=True)
    base_unit_count = fields.Float('Unit Count', compute="compute_base_product", store=True)
    base_unit_price = fields.Float("Price", compute="compute_base_product", store=True)
    base_unit_name = fields.Char('Name', compute="compute_base_product", store=True)
    lst_price = fields.Float("Product price", compute="compute_base_product", store=True)

    # default_code <= 6

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ No verification in this project, there is some case when multiple product has the same barcode"""
        pass

    def get_maturity_product(self):
        """ return all maturing of product """
        res = {}
        for product in self:
            res[product.id] = []
            if product.gestion_affinage:
                fuzzy_code = product.default_code[:-1]
                product_ids = self.env['product.product'].search([('default_code', 'like', fuzzy_code),
                                        ('default_code', '!=', product.default_code)], order='default_code')
                for product_check in product_ids:
                    if product_check.gestion_affinage and self._name == 'product.product':
                        res[product.id].append(product_check)
                    elif product_check.gestion_affinage and self._name == 'product.template':
                        res[product.id].append(product_check.product_tmpl_id)
        return res

    @api.depends('product_tmpl_id.base_unit_count', 'product_tmpl_id.base_unit_price',
                 'product_tmpl_id.list_price')
    def compute_base_product(self):
        """ NO variant """
        for product in self:
            product.base_product_id = product.product_tmpl_id.base_product_tmpl_id.product_variant_id
            product.base_unit_count = product.product_tmpl_id.base_unit_count
            product.base_unit_price = product.product_tmpl_id.base_unit_price
            product.lst_price = product.product_tmpl_id.list_price
            product.base_unit_name = product.product_tmpl_id.base_unit_name

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        """ When the product is a production, this override computes the fields :
         - 'virtual_available'
         - 'qty_available'
         - 'incoming_qty'
         - 'outgoing_qty'
         - 'free_qty'

        This override is used to get the correct quantities of products
        with 'normal' as BoM type. No production delay is used. All production is speed so use the same compute as KIT.
        """

        bom_kits = self.env['mrp.bom']._bom_find(self, bom_type='normal')
        res = super(ProductProduct, self)._compute_quantities_dict(lot_id, owner_id, package_id, from_date=from_date, to_date=to_date)
        qties = self.env.context.get("mrp_compute_quantities", {})
        qties.update(res)
        # pre-compute bom lines and identify missing BOM components to prefetch
        bom_sub_lines_per_kit = {}
        prefetch_component_ids = set()
        for product in bom_kits:
            __, bom_sub_lines = bom_kits[product].explode(product, 1)
            bom_sub_lines_per_kit[product] = bom_sub_lines
            for bom_line, __ in bom_sub_lines:
                if bom_line.product_id.id not in qties:
                    prefetch_component_ids.add(bom_line.product_id.id)
        # compute bom quantities
        for product in bom_kits:
            bom_sub_lines = bom_sub_lines_per_kit[product]
            ratios_virtual_available = []
            ratios_free_qty = []
            for bom_line, bom_line_data in bom_sub_lines:
                component = bom_line.product_id.with_context(mrp_compute_quantities=qties).with_prefetch(prefetch_component_ids)
                if component.type != 'product' or float_is_zero(bom_line_data['qty'], precision_rounding=bom_line.product_uom_id.rounding):
                    # As BoMs allow components with 0 qty, a.k.a. optionnal components, we simply skip those
                    # to avoid a division by zero. The same logic is applied to non-storable products as those
                    # products have 0 qty available.
                    continue
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id, round=False, raise_if_failure=False)
                if not qty_per_kit:
                    continue
                rounding = component.uom_id.rounding
                component_res = (
                    qties.get(component.id)
                    if component.id in qties
                    else {
                        "virtual_available": float_round(component.virtual_available, precision_rounding=rounding),
                        "free_qty": float_round(component.free_qty, precision_rounding=rounding),
                    }
                )
                ratios_virtual_available.append(component_res["virtual_available"] / qty_per_kit)
                ratios_free_qty.append(component_res["free_qty"] / qty_per_kit)
            if bom_sub_lines and ratios_virtual_available:  # Guard against all cnsumable bom: at least one ratio should be present.
                res[product.id]['virtual_available'] += min(ratios_virtual_available) * bom_kits[product].product_qty // 1
                res[product.id]['free_qty'] += min(ratios_free_qty) * bom_kits[product].product_qty // 1
        return res
