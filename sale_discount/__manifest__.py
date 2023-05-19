# See LICENSE file for full copyright and licensing details.

{
    "name": "Sale discount",
    "version": "16.0.1.0.0",
    "category": "Sale",
    "license": "AGPL-3",
    "summary": "Product Pricelist Discount",
    "author": "Mehdi Hajji",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["sale", "product_uos_pack", "sale_loyalty"],
    "data": [
        "views/product_pricelist_discount_view.xml",
        "security/ir.model.access.csv",
        "views/sale_order_view.xml",
        "views/product_product_view.xml",

    ],
    "installable": True,
}
