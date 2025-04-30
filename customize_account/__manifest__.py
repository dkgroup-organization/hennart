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
    "depends": ["account", "account_usability", "account_payment", "stock_account", "customize_purchase", "customize_sale", "customize_stock",
                "customize_mrp", "wms_carrier",  "intrastat_product", "web"],

    "data": [
        "security/ir.model.access.csv",
        "data/cron_res_partner.xml",
        "views/res_config_view.xml",
        "views/account_move_view.xml",
        "views/account_journal_view.xml",
        "views/sale_order_view.xml",
        "views/account_move_line_views.xml",
        "views/account_invoice_report_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_quant_view.xml",
        "views/delivery_carrier_order_views.xml",

        'wizards/stock_quant_export_wizard_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            #'customize_account/static/src/js/dates.js',
        ],
    },

    "installable": True,
}
