# This file is part of an Adiczion's Module.
# The COPYRIGHT and LICENSE files at the top level of this repository
# contains the full copyright notices and license terms.
{
    'name': 'Delivery Common',
    'version': '16.0.3',
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
Delivery Common
===============

Does nothing by itself. Adds the fields and libraries usable by the modules 
that depend on it, currently:

     * a4o_delivery_colissimo
     * a4o_delivery_mydelivengo
     * a4o_delivery_chronopost

This includes:

     * Support for customs information for Colissimo and Delivengo delivery 
       methods.
     * The management of the availability periods of our delivery methods.
    """,
    'data': [
        # 'security/objects_security.xml',
        # 'security/ir.model.access.csv',
        # 'wizard/your_wizard_name.xml',
        'data/ir_cron.xml',
        'views/stock_quant_views.xml',
        'views/delivery_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
