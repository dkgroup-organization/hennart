# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'WMS Scanner custom',
    'summary': 'Custom barcode management',
    'version': '16.0.1.0.1',
    'category': 'Generic Modules/Inventory Control',
    'website': 'https://dkgroup.fr',
    'author': 'DK Group',
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'depends': [
        'wms_scanner', 'customize_product_template', 'customize_partner', 'delivery', 'stock'
    ],
    'data': [
        "security/ir.model.access.csv",
        "views/stock_lot_view.xml",
        "views/stock_weight_device_views.xml",
        "views/stock_weight_value_views.xml",
        "views/stock_picking_views_inherit.xml",
        "views/stock_move_line_views_inherit.xml",
        "views/stock_location_view.xml",
        "views/stock_quant_view.xml",
        "wizard/import_product_template.xml",

    ],
    'demo': [
    ],
    'images': [
    ],
}
