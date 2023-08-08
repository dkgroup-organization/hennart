# See LICENSE file for full copyright and licensing details.

{
    "name": "Customize purchase module",
    "version": "16.0.1.0.0",
    "category": "purchase",
    "license": "AGPL-3",
    "summary": "Customize purchase module",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["purchase", "delivery", "purchase_stock", "customize_stock"],
    "data": [
        "data/purchase_data.xml",
        "security/ir.model.access.csv",
        "views/product_supplierinfo_views_inherit.xml",
        "views/purchase_order_views_inherit.xml",
        "views/res_config_settings_views.xml",
        "views/purchase_promotion_views.xml",
        "wizard/import_promotion_views.xml",
    ],
    "installable": True,
}
