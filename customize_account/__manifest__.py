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
    "depends": ["account", "account_usability", "customize_purchase", "customize_sale", "customize_stock",
                "intrastat_product"],
    "data": [
        "views/res_config_view.xml",
        "views/invoice_view.xml",
        "views/account_journal_view.xml",



    ],
    "installable": True,
}
