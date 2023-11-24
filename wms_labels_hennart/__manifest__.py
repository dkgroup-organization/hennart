
{
    "name": "Hennart Labels",
    "version": "1.0",
    "depends": ["base_report_to_printer", "printer_zpl2", "customize_stock"],
    "author": "DK group",
    "category": "Stocks",
    "description": """
    Impression ZEBRA projet Hennart
    """,
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
