{
    'name': 'Customize Dashboard',
    'version': '16.0.1.0.0',
    'summary': 'Adds missing company_id to spreadsheet.spreadsheet for dashboard compatibility',
    'depends': [
        'spreadsheet_dashboard_oca',
        'spreadsheet_oca',
        'spreadsheet_dashboard',
        'crm',
        'base'
    ],
    'data': [
        "views/spreadsheet_dashboard_group_inherit_views.xml",
        "views/spreadsheet_dashboard_tree_inherit.xml",
        "wizards/spreadsheet_spreadsheet_import.xml"
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
