# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.tools.float_utils import float_round, float_is_zero


class ProductProduct(models.Model):
    _inherit = 'product.product'

    base_product_id = fields.Many2one("product.product", string="base product",
                                        compute="compute_base_product", store=True)
    base_unit_count = fields.Float('Unit Count', compute="compute_base_product", store=True)
    base_unit_price = fields.Float("Price", compute="compute_base_product", store=True)
    base_unit_name = fields.Char('Name', compute="compute_base_product", store=True)
    lst_price = fields.Float("Product price", compute="compute_base_product", store=True)

    # default_code <= 6

    @api.depends('product_tmpl_id')
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
        kits = self.filtered(lambda p: bom_kits.get(p))
        regular_products = self - kits
        res = (
            super(ProductProduct, regular_products)._compute_quantities_dict(lot_id, owner_id, package_id, from_date=from_date, to_date=to_date)
            if regular_products
            else {}
        )
        qties = self.env.context.get("mrp_compute_quantities", {})
        qties.update(res)
        # pre-compute bom lines and identify missing kit components to prefetch
        bom_sub_lines_per_kit = {}
        prefetch_component_ids = set()
        for product in bom_kits:
            __, bom_sub_lines = bom_kits[product].explode(product, 1)
            bom_sub_lines_per_kit[product] = bom_sub_lines
            for bom_line, __ in bom_sub_lines:
                if bom_line.product_id.id not in qties:
                    prefetch_component_ids.add(bom_line.product_id.id)
        # compute kit quantities
        for product in bom_kits:
            bom_sub_lines = bom_sub_lines_per_kit[product]
            ratios_virtual_available = []
            ratios_qty_available = []
            ratios_incoming_qty = []
            ratios_outgoing_qty = []
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
                        "qty_available": float_round(component.qty_available, precision_rounding=rounding),
                        "incoming_qty": float_round(component.incoming_qty, precision_rounding=rounding),
                        "outgoing_qty": float_round(component.outgoing_qty, precision_rounding=rounding),
                        "free_qty": float_round(component.free_qty, precision_rounding=rounding),
                    }
                )
                ratios_virtual_available.append(component_res["virtual_available"] / qty_per_kit)
                ratios_qty_available.append(component_res["qty_available"] / qty_per_kit)
                ratios_incoming_qty.append(component_res["incoming_qty"] / qty_per_kit)
                ratios_outgoing_qty.append(component_res["outgoing_qty"] / qty_per_kit)
                ratios_free_qty.append(component_res["free_qty"] / qty_per_kit)
            if bom_sub_lines and ratios_virtual_available:  # Guard against all cnsumable bom: at least one ratio should be present.
                res[product.id] = {
                    'virtual_available': min(ratios_virtual_available) * bom_kits[product].product_qty // 1,
                    'qty_available': min(ratios_qty_available) * bom_kits[product].product_qty // 1,
                    'incoming_qty': min(ratios_incoming_qty) * bom_kits[product].product_qty // 1,
                    'outgoing_qty': min(ratios_outgoing_qty) * bom_kits[product].product_qty // 1,
                    'free_qty': min(ratios_free_qty) * bom_kits[product].product_qty // 1,
                }
            else:
                res[product.id] = {
                    'virtual_available': 0,
                    'qty_available': 0,
                    'incoming_qty': 0,
                    'outgoing_qty': 0,
                    'free_qty': 0,
                }

        return res
