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
        'wms_scanner', 'customize_product_template'
    ],
    'data': [
        "views/stock_lot_view.xml"

    ],
    'demo': [
    ],
    'images': [
    ],
}
