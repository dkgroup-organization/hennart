# -*- encoding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import time
import datetime



def _lang_get(self):
    lang_pool = self.env['res.lang']
    ids = lang_pool.search([])
    return [(r['code'], r['name']) for r in ids]


class label_stock_move(models.TransientModel):
    _name = "label.stock.move"
    _description = "Print Label"

    nb_label = fields.Integer('Number of label')
    name = fields.Char('Product')
    lang = fields.Selection(_lang_get, 'Language')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    prodlot_label = fields.Char('Label production lot')
    prodlot_id = fields.Many2one('stock.lot', 'Production lot', required=True)
    prodlot2_id = fields.Many2one('stock.lot', 'Production lot 2')
    code_label = fields.Char('Code label')
    default_code = fields.Char('Code')
    date_label = fields.Char('Date label')
    date_format = fields.Char('Date format')
    date = fields.Date('Date', required=True)
    weight_label = fields.Char('Weight label')
    weight = fields.Float('Weight')
    barcode = fields.Char('Barcode')
    printer_id = fields.Many2one('barcodes.printers', 'Printer')


    def default_get(self, fields):
        prodlot_obj = self.env['stock.lot']
        product_obj = self.env['product.product']
        move_obj = self.env['stock.move.line']
        context = self.env.context
        res = {}
        res['lang'] = ('fr_FR')
        res['prodlot_label'] = _('Production lot:')
        res['code_label'] = _('Code:')
        res['date_label'] = _('Use by:')
        res['weight_label'] = _('Net weight:')
        res['nb_label'] = 1
        res['weight'] = 0.0
        product = False
        prodlot = False
        #Get the value on stock move
        if self.env.context.get('active_id') and self.env.context.get("active_model") == 'stock.move.line':
            move = move_obj.browse(self.env.context.get('active_id'))

            if move.lot_id:
                prodlot = move.lot_id

            if move.picking_id and move.picking_id.picking_type_id.sequence_code == "out":
                product = move.product_id
                #Use the weight
                res['weight'] = move.move_id.weighed or 0.0
            else:
                #picking in and internal
                product = move.product_id
        #Get the value on prodlot
        if self.env.context.get('active_id') and self.env.context.get("active_model") == 'stock.lot':
            prodlot = prodlot_obj.browse(self.env.context.get('active_id'))
            product = prodlot.product_id

        #Check if there is some value in context: product_id, prodlot_id, weight
        if context.get('product_id'):
            product = product_obj.browse(context.get('product_id'), context)
        if context.get('prodlot_id'):
            prodlot = prodlot_obj.browse(context.get('prodlot_id'), context)
        if context.get('weight'):
            res['weight'] = context.get('weight')

        #Update value
        if product:
            res['product_id'] = product.id
            res['default_code'] = product.default_code
            res['name'] = product.name
            if product.use_date:
                res['date_label'] = _("Best before:")

        if prodlot:
            res['prodlot_id'] = prodlot.id
            if prodlot.life_date:
                res['date'] = prodlot.life_date
            elif prodlot.use_date:
                res['date'] = prodlot.use_date
            res['barcode'] = prodlot.barcode
            if res['weight']:
                res['barcode'] = res['barcode'][:-6] + ("%.3f" % res['weight']).rjust(6, '0')

        if res.get('date'):
            res['date_format'] = self.on_change_date(res['date'], res['lang'])['value']['date_format']

        return res

    def barcode_generation(self):

        context = self.env.context
        for label in self:
            barcode = label.product_id.barcode

            if label.weight and barcode :
                barcode = barcode[:-6] + ("%.3f" % label.weight).rjust(6, '0')
            else:
                barcode = "0000000000"
                barcode = barcode[:-6] + '00.000'

            if label.product_id and len(label.product_id.default_code) >= 5:
                barcode = label.product_id.default_code[:5] + barcode[5:]

            if label.date:
                date_format = self.on_change_date(label.date, lang=False)['value']['date_format']

            label.write({'barcode': barcode, 'date_format': date_format})

        return True

    def on_change_date(self, date, lang=False):
        res = {}
        if date:
            date2= str(date)
            res['date_format'] = date2[8:10] + '/' + date2[5:7] + '/' + date2[0:4]
            #Todo: ENGLISH
        else:
            res['date_format'] = ''

        return {'value': res}

    def on_change_lang(self, lang, product_id):
        context = self.env.context
        context['lang'] = lang
        context['product_id'] = product_id
        fields = ['prodlot_label', 'weight_label', 'code_label', 'date_label', 'name']
        value = {}
        res = self.default_get(fields, context)
        for field in fields:
            value[field] = res[field]
        
        return {'value': value}

    def valide(self):
        #print "=========valide======", ids, context
      context = self.env.context
      label_obj = self.env['labels.templates']
      move_obj = self.env['stock.move.line']
      obj_packaging = self.env['product.packaging']

      for wizard in self: 

        #Check the data integrity
        if not wizard.prodlot_id:
            raise UserError('There is no production lot.')
        if not wizard.product_id:
            raise UserError('Warning! There is no product.')
        if not wizard.printer_id:
            raise UserError('Please, select a printer.')
        if self.env.context.get('active_id')  and self.env.context.get("active_model") == 'stock.move.line':
            move = move_obj.browse(self.env.context.get('active_id'))
            if move.product_id.id == wizard.product_id.id:
                #good product
                pass
            else:
                packaging_ids = obj_packaging.search([('product_id', '=', move.product_id.id),
                     ('product_parent_id', '=', wizard.product_id.id)])
                if not packaging_ids:
                    raise UserError('Please, The product is not good.')

        if not context.get('label_id'):
            label_ids = label_obj.search([('model_id', '=', 'label.stock.move')])
            label_id = label_ids and label_ids[0] or False
        else:
            label_id = context['label_id']

        wizard.barcode_generation()

        if label_id:
            for i in range(wizard.nb_label):
                label_obj.print_label(wizard.printer_id.id)

        return {'type': 'ir.actions.act_window_close'}



class label_picking(models.TransientModel):
    _name = "label.picking"
    _description = "Print Label"


    name = fields.Char('Picking')
    printer_id = fields.Many2one('barcodes.printers', 'Printer', required=True)
    

    def default_get(self, fields):
        context = self.env.context
        if context.get('move_ids'):
            for line in context['move_ids']:
                if line[0] != 4:
                    raise UserError('Please, Save the data before print.')
        return {}

    def valide(self):
      #print "=========valide======", ids, context
      context = self.env.context
      label_obj = self.env['labels.templates']
      obj_picking = self.env['stock.picking']
      label_stock_move_obj = self.env['label.stock.move']

      for wizard in self:

        if context.get('label_id'):
            label_id = context['label_id']
        else:
            label_ids = label_obj.search([('model_id', '=', 'label.stock.move')])
            label_id = label_ids and label_ids[0] or False

        if self.env.context.get('active_id') and self.env.context.get("active_model") == 'stock.picking':
            for picking in obj_picking.browse(self.env.context.get('active_id')):
                for move in picking.move_line_ids:
                    label_context = {
                        'active_model': 'stock.move.line',
                        'active_id': move.id,
                        'active_ids': [move.id],
                         }
                    vals_label = label_stock_move_obj.default_get(label_id.id)
                    vals_label['printer_id'] = wizard.printer_id.id
                    vals_label['product_id'] = move.product_id.id

                    
                    vals_label['prodlot_id'] = move.lot_id.id
                    vals_label['date'] = move.date
                    label_stock_move_id = label_stock_move_obj.create(vals_label)
                    label_stock_move_id.valide()

        return True





class label_container(models.TransientModel):
    _name = "label.container"
    _description = "Print Label"


    name = fields.Char('Container')
    name2 = fields.Char('Container suite')
    date = fields.Char('Date')
    barcode = fields.Char('barcode')
    nb_container = fields.Integer('Nb Containers and pallets')
    nb_total_container = fields.Integer('Nb Total Containers and pallets')
    street = fields.Char('street')
    street2 = fields.Char('street2')
    zip = fields.Char('zip')
    city = fields.Char('city')
    country = fields.Char('country')
    partner_name = fields.Char('partner_name')
    printer_id = fields.Many2one('barcodes.printers', 'Printer')
    

    def default_get(self, fields):
        

        picking_obj = self.env['stock.picking']
        context = self.env.context
        if self.env.context.get('active_id') and self.env.context.get("active_model") == 'stock.picking':
            picking = picking_obj.browse(self.env.context.get('active_id'))
            res['nb_container'] = context.get('nb_container') or 1
            res['nb_total_container'] = picking.nb_container or 1
            res['printer_id'] = False
            res['name'] = picking.carrier_id and picking.carrier_id.name or ''
            if picking.partner_id:
                res['partner_name'] = picking.partner_id.name or ''
                res['street'] = picking.partner_id.street or ''
                res['street2'] = picking.partner_id.street2 or ''
                res['zip'] = picking.partner_id.zip or ''
                res['city'] = picking.partner_id.city or ''
                res['country'] = picking.partner_id.country_id and picking.partner_id.country_id.name or ''

        return res

    def valide(self):
        #print "=========valide====label_container==", ids, context
      context = {}
      label_obj = self.env['labels.templates']
      picking_obj = self.env['stock.picking']

      for wizard in self:
        #Check the data integrity
        if not wizard.printer_id:
            raise UserError('Please, select a printer.')
        elif self.env.context.get('active_id') and self.env.context.get("active_model") == 'stock.picking':
            picking = picking_obj.browse(self.env.context.get('active_id'))

        if not context.get('label_id'):
            label_ids = label_obj.search([('model_id', '=', 'label.container')])
            label_id = label_ids and label_ids[0] or False
        else:
            label_id = context['label_id']

        nb_total_container = picking.nb_container + picking.nb_pallet
        sscc_lines_ids = []
        for sscc in picking.sscc_lines_ids:
            sscc_lines_ids.append(sscc.id)

        todo_sscc = nb_total_container - len(sscc_lines_ids)
        if todo_sscc == 0:
            pass
        elif todo_sscc > 0:
            #create sscc
            for i in range(todo_sscc):
                new_id = self.env['stock.sscc'].create({'picking_id': picking.id})
                sscc_lines_ids.append(new_id)
        else:
            #delete sscc
            for i in range(-todo_sscc):
                self.env['stock.sscc'].unlink([sscc_lines_ids.pop()])

        sscc_lines_ids.reverse()

        for number_label_container in range(nb_total_container):
            context['nb_container'] = number_label_container + 1
            context['nb_total_container'] = nb_total_container

            if len(sscc_lines_ids) > 0:
                sscc_id = sscc_lines_ids.pop()
                sscc = self.env['stock.sscc'].browse(sscc_id)
                context['barcode'] = sscc.name
            else:
                context['barcode'] = ''

            if picking.date_delivered:
                context['date'] = picking.date_delivered[8:10] + '/' + picking.date_delivered[5:7] + '/' + picking.date_delivered[:4]
            else:
                context['date'] = ''

            if picking.partner_id.carrier_zone:
                context['name2'] = picking.partner_id.carrier_zone
            elif picking.partner_id.parent_id and picking.partner_id.parent_id.carrier_zone:
                context['name2'] = picking.partner_id.parent_id.carrier_zone
            else:
                context['name2'] = ''

            #print "============label_id=======", label_id, ids, wizard.printer_id.id, context
            label_obj.print_label([], wizard.printer_id.id)
            label_obj.print_label( [], wizard.printer_id.id)

        return {'type': 'ir.actions.act_window_close'}


