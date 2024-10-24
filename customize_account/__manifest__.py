# See LICENSE file for full copyright and licensing details.

{
    "name": "Customize account module",
    "version": "16.0.1.0.0",
    "category": "Account",
    "license": "AGPL-3",
    "summary": "Customize account module",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["account", "account_usability", "account_payment", "customize_purchase", "customize_sale", "customize_stock",
                "customize_mrp", "intrastat_product"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_view.xml",
        "views/account_move_view.xml",
        "views/account_journal_view.xml",
        "views/sale_order_view.xml",
        "views/stock_picking_views.xml",
        "views/account_move_line_views.xml",

    ],
    "installable": True,
}
