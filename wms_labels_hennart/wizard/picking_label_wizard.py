from odoo import models, fields, api

class PickingLabelWizard(models.TransientModel):
    _name = 'picking.label.wizard'
    _description = 'Wizard for Printing Labels'

    picking_id = fields.Many2one('stock.picking', string='Transfer')
    printer_id = fields.Many2one('printing.printer', string="Printer")
    move_line_ids = fields.One2many('picking.label.wizard.line', 'wizard_id', string='Move Lines')

    def print_labels(self):
        """ Print label """
        self.ensure_one()
        label_id = self.env['printing.label.zpl2'].search([('model_id.model', '=', 'stock.lot')])

        if self.printer_id and label_id:
            for line in self.move_line_ids:
                if line.lot_id:
                    label_qty = line.label_qty
                    while label_qty > 0:
                        label_id.print_label(self.printer_id, line.lot_id)
                        label_qty -= 1


class PickingLabelWizardLine(models.TransientModel):
    _name = 'picking.label.wizard.line'
    _description = 'Wizard Line for Picking Labels'

    wizard_id = fields.Many2one('picking.label.wizard', string='Wizard')
    move_line_id = fields.Many2one('stock.move.line', string='Stock Move Line')
    product_id = fields.Many2one('product.product', related="move_line_id.product_id")
    lot_id = fields.Many2one('stock.lot', related="move_line_id.lot_id")
    quantity = fields.Float(string='Quantity')
    label_qty = fields.Integer(string='Labels to Print', default=1)
