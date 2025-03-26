

{
    "name": "Hennart Custom reports",
    "version": "16.0.1.1.1",
    "category": "Misc",
    "license": "AGPL-3",
    "author": "Mehdi HAJJI ",
    "website": "https://dkgroup.fr/",
    "depends": ["web", "sale", "account", "stock", "customize_sale",
                "customize_stock", "customize_account", "wms_carrier"],
    "data": [
        "views/external_layout_inherit.xml",
        "views/report_invoice.xml",
        "views/sale_portal_report.xml",
        "views/sale_report.xml",
        "views/res_company_view.xml",
        "views/report_purchasequotation_document_inherit.xml",
        "views/report_invoice_bl_valued.xml",
        "views/report_delivery_document_hennart.xml",
        "views/stock_picking_views.xml",
        "views/report_delivery_carier_order.xml",

        "reports/account_invoices_bl_valued.xml",
        "reports/stock_picking_hennart.xml",
        "reports/delivery_carrier_order.xml",
    ],
}
