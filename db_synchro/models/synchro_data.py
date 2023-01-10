# See LICENSE file for full copyright and licensing details.

#Configuration data,

# minimum date to search, can be use to limit the load of data
MIN_DATE = '2000-01-01'

# corresponding field, this dictionary content the current mapping of fields identified betwen version
MAP_FIELDS_V7 = {'account.invoice': {
                    'invoice_line_ids': 'invoice_line',
                    'tax_line_ids': 'tax_line',
                    'payment_term_id': 'payment_term'},

                'account.invoice.line': {'invoice_line_tax_ids': 'invoice_line_tax_id'},
                'account.payment': {'communication': 'name', 'name': 'number'}
                }

MAP_FIELDS_V10 = {}

MAP_FIELDS = {'7': MAP_FIELDS_V7,
             '8': {},
             '9': {},
             '10': MAP_FIELDS_V10,
             '11': {},
             '12': {},
             '13': {},
             '14': {},
             '15': {},
             '16': {},
             }

# preconfiguration option to use when the object is created
OPTIONS_OBJ = {
    'res.company': {'except_fields': ['parent_id', 'user_ids'], 'auto_update': True},
    'ir.module.module': {'domain': [('state', '=', 'installed')], 'auto_search': True},
    'res.currency': {'auto_search': True, 'search_field': 'symbol', 'state': 'manual'},
    'res.bank': {'auto_create': True},
    'res.partner.bank': {'auto_create': True},
    'res.groups': {'auto_search': True},
    'res.lang': {'auto_search': True, 'search_field': 'iso_code', 'state': 'auto'},
    'res.users': {'except_fields': ['alias_id', 'groups_id', 'action_id'], 'auto_search': True,
                  'search_field': 'login'},
    'res.partner': {'except_fields': ['vat', 'message_follower_ids', 'signup_expiration', 'user_id',
                                      'commercial_partner_id', 'signup_token', 'category_id'],
            'auto_search': True, 'auto_create': True, 'domain': [('id', '>', 5)]},

    'uom.uom': {'auto_search': True, 'state': 'manual'},
    'product.category': {'auto_search': True, 'auto_create': True, 'auto_update': True},
    'product.template':  {'auto_create': True, 'auto_update': True},
    'product.product':  {'auto_create': True, 'auto_update': True},
    'account.tax': {'auto_search': True},
    'stock.location.route': {'auto_search': True},
    'product.color': {'auto_create': True, 'auto_update': True},
    'product.material': {'auto_create': True, 'auto_update': True},
    'product.manufacturing.area':	 {'auto_create': True, 'auto_update': True},
    'product.type': {'auto_create': True, 'auto_update': True},
    'res.country': {'auto_search': True, 'state': 'auto'},
    'res.country.state': {'auto_search': True, 'auto_create': True, 'auto_update': True},
    'res.partner.title': {'auto_search': True, 'auto_create': False, 'auto_update': True},
    'res.partner.category': {'auto_search': True, 'auto_create': True, 'auto_update': True, 'state': 'auto',
                             'except_fields': ['partner_ids']},
    'crm.team': {'auto_search': True, 'auto_create': True, 'auto_update': True},
    'account.journal': {'auto_search': True},
    'account.account': {'auto_search': True, 'search_field': 'code'},
    'calendar.event':  {'state': 'cancel'},

    }




