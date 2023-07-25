# See LICENSE file for full copyright and licensing details.

{
    "name": "Customize sale module",
    "version": "16.0.1.0.0",
    "category": "sale",
    "license": "AGPL-3",
    "summary": "Customize sale module",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["account", "sale", "stock", "sale_stock", "sale_mrp", "crm_phonecall",
                "delivery", "customize_product_template", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_view.xml",
        "views/product_pricelist_view.xml",
        "wizard/import_pricelist_view.xml",

    ],
    "installable": True,
}
