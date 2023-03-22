

from odoo import models, fields ,api, _
import time
import datetime


class delivery_carrier_order(models.Model):

    _name = "delivery.carrier.order"
    _description = "Carrier Order"
    _inherit = ['mail.thread']

    def _update_info(self):
        res = {}
        date_now = time.strftime('%Y-%m-%d %H:%M:%S')
        for carrier_order in self:
          if carrier_order:
            order_date = carrier_order.date_expected or date_now
            nagel_name = 'DZV_HENNART____CALTMS_IMP_AUFTRAEGE_'
            nagel_counter = str(order_date).replace('-', '')
            carrier_order.number_of_packages= 0
            carrier_order.nb_picking= 0
            carrier_order.nb_line=0
            carrier_order.nb_container=0
            carrier_order.nb_pallet= 0
            carrier_order.nb_pallet_europe= 0
            carrier_order.nb_pallet_perdu= 0
            carrier_order.weight= 0
            date = carrier_order.date_expected or date_now
            carrier_order.nb_picking = len(carrier_order.picking_ids)
            if carrier_order.picking_ids: 
             for picking in carrier_order.picking_ids:
                carrier_order.nb_line += len(picking.move_line_ids)
                carrier_order.number_of_packages += picking.number_of_packages
                carrier_order.nb_container += picking.nb_container
                carrier_order.nb_pallet += picking.nb_pallet
                carrier_order.nb_pallet_europe += picking.nb_pallet_europe
                carrier_order.nb_pallet_perdu += picking.nb_pallet_perdu
                date_delivered = picking.scheduled_date + datetime.timedelta(days=1)
                carrier_order.date_delivered = date_delivered.strftime('%Y-%m-%d 12:00:00')
                for line in picking.move_ids:
                    carrier_order.weight += line.weight

    def check_state(self):
        for order in self:
            test = order.state
            if order.state not in ['cancel', 'done']:
                states = []
                for picking in order.picking_ids:
                    if picking.state not in states:
                        states.append(picking.state)
                if "draft" in states:
                    test = 'confirmed'
                elif 'confirmed' in states:
                    test = 'confirmed'
                elif 'assigned' in states:
                    test = 'assigned'
                elif 'done' in states:
                    test = 'done'
                elif 'cancel' in states:
                    test = 'cancel'
            if order.state != test:
               order.write({'state': test})
        return order

    
    def button_action_done(self):
        context = {}
        location_obj = self.env['stock.location']
        move_obj = self.env['stock.move']
        picking_obj = self.env['stock.picking']
        location_ids = location_obj.search([('usage', '=', 'customer')])
        customer_location_id = location_ids[0]
        move_output_ids = []
        picking_ids = []
        for order in self:
            for picking in order.picking_ids:
                picking_ids.append(picking.id)
                for move in picking.move_line_ids:
                    if move.state == 'done':
                        move_output_ids.append(move.id)
        date_done = picking.scheduled_date
        moves = move_obj.search([('id','in',move_output_ids)])
        for mm in moves:
         mm.write({
            'location_dest_id': customer_location_id,
            'date': date_done,
          
            })

        for order in self:
            for picking in order.picking_ids:
                if picking.state in ['assigned', 'confirmed','waiting']:
                    picking.button_validate()
        self.check_state()
        return True

    @api.depends('date_expected')
    def compute_date_exep(self):
        for rec in self:
            if  rec.date_expected :
                rec.date_expected2 = rec.date_expected.date()
            else:
                rec.date_expected2 = False

    edi_done = fields.Boolean('EDI Already sending')
    carrier_id = fields.Many2one("delivery.carrier", "Carrier")
    date_done = fields.Datetime('Date of Transfer', index=True, help="Date of Completion")
    date_expected = fields.Datetime('Date expected', index=True, help="Date", readonly=True)
    date_delivered = fields.Date(compute="_update_info")
    date_expected2 = fields.Date(compute="compute_date_exep", store=True )
    hour_expected = fields.Float('Hour expected')
    name = fields.Char('description')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True, states={'done': [('readonly', True)]})
    picking_ids = fields.One2many('stock.picking', 'carrier_order_id', 'Delivery Order')
    state = fields.Selection([
                        ('cancel', 'Cancelled'),
                        ('draft', 'Draft'),
                        ('confirmed', 'Waiting'),
                        ('assigned', 'Available'),
                        ('done', 'Done'),
                        ], 'Status', index=True)

  
    weight = fields.Float(compute="_update_info", string='Weight')
    nb_line = fields.Integer(compute="_update_info", string='Nb line',)
    nb_picking = fields.Integer(compute="_update_info", string='Nb picking',)
    number_of_packages = fields.Integer(compute="_update_info", string='Nb packages')
    nb_container = fields.Integer(compute="_update_info", string='Nb container',)
    nb_pallet = fields.Integer(compute="_update_info", string='Nb pallet',)
    nb_pallet_europe = fields.Integer(compute="_update_info", string='Nb Pallets europes')
    nb_pallet_perdu = fields.Integer(compute="_update_info", string='Nb Pallets Perdus')
    nb_pallet_ground = fields.Integer('Nb Pallets on Ground')

    driver_name = fields.Char('Driver name')
    temperature = fields.Float('Temperature')
    note = fields.Text('Comment')

