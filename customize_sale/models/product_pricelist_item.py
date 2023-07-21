
from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _
from odoo.tools import format_datetime, formatLang


class PriceListInherit(models.Model):
    _inherit = 'product.pricelist.item'

    product_code = fields.Char(string="Product Code", related="product_id.default_code", index=True, store=True)

    applied_on = fields.Selection(
        selection=[
            ('3_global', "All Products"),
            ('2_product_category', "Product Category"),
            #('1_product', "Product"),
            ('0_product_variant', "Product Variant"),
        ],
        string="Apply On",
        default='0_product_variant',
        required=True,
        help="Pricelist Item applicable on selected option")

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _compute_name_and_price(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = item.product_id.with_context(display_default_code=False).display_name
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                item.price = formatLang(
                    item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount", item.percent_price)
            else:
                item.price = _("%(percentage)s %% discount and %(price)s surcharge",
                               percentage=item.price_discount, price=item.price_surcharge)
