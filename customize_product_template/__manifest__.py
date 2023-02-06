# See LICENSE file for full copyright and licensing details.

{
    "name": "Customize product template",
    "version": "16.0.1.0.0",
    "category": "sale",
    "license": "AGPL-3",
    "summary": "Customize product add fields",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["account", "sale", "sale_stock", "product_expiry"],
    "data": [
        'security/ir.model.access.csv',
        "views/product_template.xml",


    ],
    "installable": True,
}
