# See LICENSE file for full copyright and licensing details.

{
    "name": "Customize MRP",
    "version": "16.0.1.0.0",
    "category": "Manufacturing",
    "license": "AGPL-3",
    "summary": "Customize MRP",
    "author": "DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["base", "mrp", "stock", "sale_stock",  "product_expiry", "customize_product_template", "wms_planning"],
    "data": [
         "views/mrp_production_view.xml",
    ],
    "installable": True,

}
