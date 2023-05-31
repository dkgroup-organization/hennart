
from odoo import models
from odoo import fields ,api


class stock_picking(models.Model):
    _inherit = "stock.picking"
    sscc_lines_ids = fields.One2many('stock.sscc', 'picking_id', 'Code colis SSCC')
    nb_sscc_label = fields.Integer('Needed sscc label:')


    @api.model
    def create(self, vals):
        obj = super(stock_picking, self).create(vals)
        obj.update_sscc()
        return obj

    def write(self,values):
        
        override_write = super(stock_picking,self).write(values)
        self.update_sscc()
        return override_write

    # @api.onchange('nb_sscc_label')
    def update_sscc(self):
        for picking in self:
            # nb_total_container = picking.nb_container + picking.nb_pallet
            nb_total_container = picking.nb_sscc_label
            sscc_lines_ids = []
            for sscc in picking.sscc_lines_ids:
                sscc_lines_ids.append(sscc.id)
            todo_sscc = nb_total_container - len(sscc_lines_ids)
            if todo_sscc == 0:
                pass
            elif todo_sscc > 0:
                #create sscc
                for i in range(todo_sscc):

                    new_idd = self.env['stock.sscc'].create({'picking_id':picking.id})
                    new_idd.picking_id = picking.id
                    sscc_lines_ids.append(new_idd.id)
            else:
         
                for i in range(-todo_sscc):
                    test = self.env['stock.sscc'].search([('picking_id','=',picking.id)],order="id desc", limit=1)

                    test.unlink()

 




