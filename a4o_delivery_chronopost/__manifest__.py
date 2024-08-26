# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
{
    'name': 'Chronopost Shipping',
    'version': '16.1.7',
    'author': 'Adiczion SARL',
    'category': 'Adiczion',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr',
        'delivery',
        'mail',
        'a4o_delivery_common',
        'a4o_delivery_relaypoint',
        ],
    'external_dependencies': {'python': ['suds-community']},
    'demo': [],
    'website': 'http://adiczion.com',
    'description': """
Chronopost Shipping
===================

Send your shippings through Chronopost and track them online.

    """,
    'data': [
        # 'security/objects_security.xml',
        'security/ir.model.access.csv',
        'data/delivery_chronopost_data.xml',
        'views/delivery_chronopost_views.xml',
        # 'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/select_printer_views.xml',
        ],
    'images': ['static/description/banner.png'],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
