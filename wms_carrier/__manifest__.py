
{
"name" : "Carrier module of the WMS",
    "category" : "Generic Modules",
    "version" : "16.0",
    "depends": ["delivery", "sale"],
    "author" : "Abdelghani KHALIDI DK Group",
    "license": "AGPL-3",
    "description": """
    carrier module for the Warehouse Management System:
    """,
    "data": [
        "security/ir.model.access.csv",
        "view/carrier_view.xml",
        "view/stock_picking_view.xml",
        ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
