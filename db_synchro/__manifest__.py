# See LICENSE file for full copyright and licensing details.

{
    "name": "Multi-DB Synchronization",
    "version": "16.0.1.0.0",
    "category": "Tools",
    "license": "AGPL-3",
    "summary": "Multi-DB Synchronization",
    "author": "OpenERP SA, Serpent Consulting Services Pvt. Ltd., opencrea, DKgroup",
    "website": "https://dkgroup.fr",
    "maintainer": "DK group",
    "images": [],
    "depends": ["base", "sale", "customize_stock", "queue_job", "customize_account", "customize_product_template", "customize_partner",
                "customize_scanner", "list_view_sticky_header", "wms_planning"],
    "data": [
        "views/synchro_menu.xml",
        "views/synchro_server_view.xml",
        "views/synchro_obj_view.xml",
        "views/synchro_obj_line_view.xml",
        "security/ir.model.access.csv",
        "views/cron.xml",
    ],
    "installable": True,
}
