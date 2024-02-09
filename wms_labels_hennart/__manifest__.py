
{
    "name": "Hennart Labels",
    "version": "1.0",

    'website': 'https://dkgroup.fr',
    'author': 'DK Group',
    "category": "Stocks",
    "license": "AGPL-3",
    'summary': 'Custom label',
    "description": """
    Impression ZEBRA projet Hennart
    """,
    "depends": ["base_report_to_printer", "printer_zpl2", "customize_stock", "wms_sscc"],
    "data": [
        #"security/ir.model.access.csv","data/label.xml",
        #"wizard/label_stock_move_view.xml",
        "data/printing_label_zebra.xml",
        "data/printing_label_component_zebra.xml",
        "views/printing_printer.xml",

    ],
    'installable': True,
    'active': False,
}
