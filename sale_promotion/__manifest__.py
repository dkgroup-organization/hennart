{
    'name': 'Sale Promotion',
    'version': '16.0.1.0',
    'summary': 'Module de gestion des promotions sur les ventes',
    'category': 'Sales',
    'author': 'Mehdi Hajji',
    'depends': ['sale'],
    'data': [
        'views/sale_promotion_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
