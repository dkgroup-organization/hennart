# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'WMS Scanner',
    'summary': 'Allows managing barcode readers with complex scenarios',
    'version': '16.0.1.0.1',
    'category': 'Generic Modules/Inventory Control',
    'website': 'https://dkgroup.fr',
    'author': 'DK Group',
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'depends': [
        'product',
        'stock',
        'web_pwa_oca'
    ],
    'data': [
        'security/ir.model.access.csv',
        
        'views/wms_scenario.xml',
        'views/wms_session.xml',
        'views/wms_menu.xml',
        'views/menu.xml',

        'views/wms_scanner_image_template.xml',
        'views/wms_scanner_menu_template.xml',
        'views/wms_scanner_scenario_info_template.xml',

    ],
    'demo': [
    ],
    'images': [
    ],
}
