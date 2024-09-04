# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
{
    'name': 'Delivery Relay Points',
    'version': '16.1.4',
    'author': 'Adiczion SARL',
    'category': 'Adiczion',
    'license': 'AGPL-3',
    'depends': [
        'stock',
        'delivery',
    ],
    'demo': [],
    'website': 'http://adiczion.com',
    'description': """
Delivery Relay Points
=====================

Does nothing alone, adds the management of relay points to the transport
modules that depend on it.

    """,
    'data': [
        'security/objects_security.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/delivery_views.xml',
        'wizard/choose_delivery_package_views.xml',
        'wizard/select_relaypoint_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
