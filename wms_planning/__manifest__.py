
{
    "name" : "Stock plannification",
    "category" : "Generic Modules",
    "version" : "16.0",
    "depends": ["stock", "mrp", "delivery"],
    "author" : "Joannes LANDY, DK Group",
    "license": "AGPL-3",
    "description": """
    Stock prevision for the Warehouse Management System:
    """,
    "data": [
        "security/ir.model.access.csv",

        "views/report_stock_prevision.xml",

    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}


