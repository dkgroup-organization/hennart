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
        'wms_scanner', 'customize_stock', 'base_module_record', 'wms_labels_hennart'
    ],
    'data': [
        "views/scenario_input_template.xml",
        "views/scenario_preparation_list_template.xml",
        "views/scenario_preparation_line_template.xml",
        "views/scenario_preparation_message_template.xml",
        "views/scenario_move_template.xml",
        "views/scenario_inventory_template.xml",
        "views/scenario_change_lot_template.xml",
        "views/scenario_print_template.xml",
        "views/scenario_weight_template.xml",
        "views/scenario_production_list_template.xml",
        "views/scenario_production_line_template.xml",

        "data/scenario_preparation.xml",
        "data/scenario_preparation_transition.xml",
        "data/scenario_move.xml",
        "data/scenario_move_transition.xml",
        "data/scenario_inventory.xml",
        "data/scenario_inventory_transition.xml",
        "data/scenario_change_lot.xml",
        "data/scenario_change_lot_transition.xml",
        "data/scenario_production.xml",
        "data/scenario_production_transition.xml",
        "data/scenario_print.xml",
        "data/scenario_print_transition.xml",
        "data/scenario_weight.xml",
        "data/scenario_weight_transition.xml",

        "data/scenario_menu.xml",
    ],
    'demo': [
    ],
    'images': [
    ],
}
