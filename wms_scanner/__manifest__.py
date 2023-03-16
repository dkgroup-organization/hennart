# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'WMS Scanner',
    'summary': 'Allows managing barcode readers with complex scenarios',
    'version': '14.0.1.0.1',
    'category': 'Generic Modules/Inventory Control',
    'website': 'https://dkgroup.fr',
    'author': 'DK Group',
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'depends': [
        'product',
        'stock',
    ],
    'data': [

        
        'views/wms_scenario.xml',
        'views/wms_menu.xml',
        'views/menu.xml',

        'views/wms_scanner_menu_template.xml',
        'views/wms_scanner_input_fields_template.xml',
        'views/wms_scanner_scenario_info_template.xml',
        'views/wms_scanner_scenario_move_template.xml',

        'views/wms_scanner_zxing_template.xml',
        'views/wms_scanner_zxing2_template.xml',

        'security/ir.model.access.csv',

    ],
    'demo': [
    ],
    'images': [
    ],
}
