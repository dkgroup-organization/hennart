# See LICENSE file for full copyright and licensing details.

{
    "name": "Import Price List",
    "version": "16.0.1.0.0",
    "category": "sale",
    "license": "AGPL-3",
    "summary": "Import Price List",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "images": [],
    "depends": ["purchase", "sale", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/import_pricelist_views.xml",
    ],
    "installable": True,
}
