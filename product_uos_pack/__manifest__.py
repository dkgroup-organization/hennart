# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product UOS and pack',
    'version': '16.0.1',
    'category': 'Base',
    'summary': 'product packaging and UOS',
    'description': """
This module contains the customization packaging and uos management.
secondary Unit of sale is used to invoice in kg.

    """,
    'depends': ['sale', 'stock', 'sale_stock', 'delivery', 'account'],
    'data': [
        'security/ir.rule.xml',

        'views/sale_view.xml',
        'views/product_view.xml',


    ],
    'demo': [

    ],
    'installable': True,
    'auto_install': False
}
