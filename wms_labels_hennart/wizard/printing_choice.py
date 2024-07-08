from odoo import _, api, fields, models

class PrintingChoice(models.TransientModel):
    _name = "printing.choice"
    _description = "choice printer"

    name = fields.Char('description')
    printer_id = fields.Many2one('printing.printer', string="Printer")
    picking_id = fields.Many2one('stock.picking', string="Picking")

    def print_container_label(self):
        """ Print container label """
        self.ensure_one()
        if self.picking_id and self.printer_id:
            self.picking_id.print_container_label(printer=self.printer_id)

