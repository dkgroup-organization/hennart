# @@ -1,11 +1,10 @@
# Copyright 2017 Tecnativa - Vicent Cubells

{
    "name": "CRM Phone Calls",
    "version": "16.0.1.0.2",
    "category": "Customer Relationship Management",
    "author": "Odoo S.A., Tecnativa, Odoo Community Association (OCA), DK Group",
    "website": "https://github.com/dkgroup-organization/hennart",
    "license": "AGPL-3",
    "depends": ["crm", "calendar", "delivery", "sale", "account"],
    "data": [
        "security/crm_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "wizard/crm_phonecall_to_phonecall_view.xml",
        "views/crm_phonecall_view.xml",
        "views/res_partner_view.xml",
        "views/crm_lead_view.xml",
        "views/res_config_settings_views.xml",
        "report/crm_phonecall_report_view.xml",
    ],
    "installable": True,
}
