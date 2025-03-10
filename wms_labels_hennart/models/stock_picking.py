
from odoo import models, fields ,api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def print_container_label(self, printer=None):
        """ Create package to label"""
        for picking in self:
            picking.update_sscc()
            if printer:
                picking.sscc_line_ids.print_label(printer=printer)

    def print_label(self, printer=None, label_id=None):
        """ Print label if information ready """
        for picking in self:
            if printer:
                picking.move_line_ids.print_label(printer=printer, label_id=label_id)

    def open_label_wizard(self):

        wizard = self.env['picking.label.wizard'].create({'picking_id': self.id})

        lot_ids = {}
        for line in self.move_line_ids:
            if line.lot_id and line.lot_id not in list(lot_ids.keys()):
                lot_ids[line.lot_id] = {'move_line': line, 'quantity': line.qty_done}
            else:
                lot_ids[line.lot_id]['quantity'] += line.qty_done

        for lot_id in lot_ids.keys():
            wizard.move_line_ids.create({
                'wizard_id': wizard.id,
                'move_line_id': lot_ids[lot_id]['move_line'].id,
                'quantity': lot_ids[lot_id]['quantity'],
                'label_qty': 1
            })

        return {
            'name': 'Print Labels',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'picking.label.wizard',
            'res_id': wizard.id,
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }
