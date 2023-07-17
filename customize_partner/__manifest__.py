# See LICENSE file for full copyright and licensing details.

{
    "name": "Customize partner",
    "version": "16.0.1.0.0",
    "category": "Contact",
    "license": "AGPL-3",
    "summary": "Customize partner",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["base", "account", "sale_stock", "delivery", "crm_phonecall"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_area_view.xml",
        "views/res_partner_function_view.xml",
        "views/res_partner_view.xml",

        #"data/res.partner.function.csv",
    ],
    "installable": True,

}
