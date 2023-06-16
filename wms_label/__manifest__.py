

{
    "name" : "Industrial barcode label",
    "description" : "Print barcode label with industrial printers like SATO or Zebra",
    "version" : "2.2",
    "author" : "Dkgroup",
    "category" : "",
    "depends" : ["stock","base_report_to_printer","wms_sscc"],
    "data":["security/ir.model.access.csv",'view/barcode_printer_view.xml','view/label_template_view.xml'],
    'installable': True,
    'active': False,
}

