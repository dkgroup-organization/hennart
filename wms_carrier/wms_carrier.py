#!/usr/bin/env python
##############################################################################
#
#    Copyright 2015 OpenCrea (<http://opencrea.fr>)
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models
from odoo import fields ,api
from odoo import _
import openerp.addons.decimal_precision as dp
from odoo import SUPERUSER_ID
from odoo import netsvc
import unicodedata
import time
import datetime
from dateutil.relativedelta import relativedelta
import pytz
import base64
# import pysftp
import os

# mounting directory with chronopost files
CHRONO_MNT = '/mnt/scrutchronoposte'

class mail_mail(models.Model):

    _inherit = 'mail.mail'

    def send_get_mail_subject(self, mail, force=False, partner=None):
        """ If subject is void and record_name defined: '<Author> posted on <Resource>'
        except for delivery_carrier_order and EDI

            :param boolean force: force the subject replacement
            :param browse_record mail: mail.mail browse_record
            :param browse_record partner: specific recipient partner
        """
        if mail.model == 'delivery.carrier.order' and not mail.subject:
            return ''
        elif (force or not mail.subject) and mail.record_name:
            return 'Re: %s' % (mail.record_name)
        elif (force or not mail.subject) and mail.parent_id and mail.parent_id.subject:
            return 'Re: %s' % (mail.parent_id.subject)
        return mail.subject


class delivery_carrier_order(models.Model):

    _name = "delivery.carrier.order"
    _description = "Carrier Order"
    _inherit = ['mail.thread']

    def _update_info(self):
        res = {}
        # timeline_obj = self.env['timeline.day']
        date_now = time.strftime('%Y-%m-%d %H:%M:%S')


        for carrier_order in self:
          if carrier_order:
            #init variable
            order_date = carrier_order.date_expected or date_now
            nagel_name = 'DZV_HENNART____CALTMS_IMP_AUFTRAEGE_'
            nagel_counter = str(order_date).replace('-', '')
            carrier_order.number_of_packages= 0
            carrier_order.nb_picking= 0
            carrier_order.nb_line=0
            carrier_order.nb_container=0
            carrier_order.nb_pallet= 0
            carrier_order.weight= 0
            
            date = carrier_order.date_expected or date_now
            carrier_order.nb_picking = len(carrier_order.picking_ids)
            if carrier_order.picking_ids: 
             for picking in carrier_order.picking_ids:

                carrier_order.nb_line += len(picking.move_line_ids)
                carrier_order.number_of_packages += picking.number_of_packages
                carrier_order.nb_container += picking.nb_container
                carrier_order.nb_pallet += picking.nb_pallet

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
                        state.append(picking.state)

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

        #Change the location of the stock move to customer
        for order in self:
            for picking in order.picking_ids:
                picking_ids.append(picking.id)
                output_location_id = picking.warehouse_id.lot_output_id.id
                for move in picking.move_line_ids:
                    if move.state == 'done' and move.location_dest_id.id == output_location_id:
                        move_output_ids.append(move.id)

        date_done = picking.scheduled_date + time.strftime(' %H:%M:%S')
        move_obj.write(move_output_ids, {
            'location_dest_id': customer_location_id,
            'date_expected': date_done,
            'date': date_done,
            })

        #Admin change the state
        picking_obj.check_state(picking_ids)

        for order in self:
            for picking in order.picking_ids:
                if picking.state in ['assigned', 'done']:
                    picking_obj.action_done([picking.id])

        self.check_state(ids)
        for order in self:
            if order.state == 'done' and order.edi_done is False:
                self.button_action_send([order.id])

            if order.state == 'done':
                for picking in order.picking_ids:
                    try:
                        picking_obj.button_action_send([picking.id])
                    except:
                        pass

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
    date_expected = fields.Datetime('Date expected', index=True, help="Date", widget="date", readonly=True)
    date_delivered = fields.Date(compute="_update_info", method=True )
    date_expected2 = fields.Date(compute="compute_date_exep", store=True )
    hour_expected = fields.Float('Hour expected', widget="float_time")
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

  
    weight = fields.Float(compute="_update_info", string='Weight', digits=dp.get_precision('Stock Weight'))
    nb_line = fields.Integer(compute="_update_info", string='Nb line',)
    nb_picking = fields.Integer(compute="_update_info", string='Nb picking',)
    number_of_packages = fields.Integer(compute="_update_info", string='Nb packages')
    nb_container = fields.Integer(compute="_update_info", string='Nb container',)
    nb_pallet = fields.Integer(compute="_update_info", string='Nb pallet',)
    nb_pallet_europe = fields.Integer('Nb Pallets europe')
    nb_pallet_perdu = fields.Integer('Nb Pallets Perdu')
    nb_pallet_ground = fields.Integer('Nb Pallets on Ground')

    driver_name = fields.Char('Driver name')
    temperature = fields.Float('Temperature')
    note = fields.Text('Comment')

class stock_picking(models.Model):
    _inherit = "stock.picking"

    def action_confirm(self):
        carrier_order_obj = self.env['delivery.carrier.order']
        for picking in self:
            if picking.carrier_id:
                date_pikcing = picking.scheduled_date.date()

                carrier_order_id = carrier_order_obj.search([('carrier_id', '=', picking.carrier_id.id),('date_expected2','=',date_pikcing)])
                if carrier_order_id:
                    picking.carrier_order_id = carrier_order_id.id
                else:
                    carrier_order_name = picking.carrier_id.name
                    carrier_order_vals = {
                        'name': carrier_order_name or "",
                        'carrier_id': picking.carrier_id.id,
                        'date_expected': picking.scheduled_date,
                        # 'hour_expected' : float(picking.scheduled_date.time()),
                        'warehouse_id': 1,
                        'nb_picking': 1,
                        'nb_line': len(picking.move_line_ids),
                        'weight': picking.weight,
                        'state': 'confirmed'
                        }
                    carrier_order_id = carrier_order_obj.create(carrier_order_vals)
                    picking.carrier_order_id = carrier_order_id.id
        return super(stock_picking,self).action_confirm()

        
    carrier_order_id = fields.Many2one('delivery.carrier.order',string='Carrier order')
    nb_container = fields.Integer('Number of container')
    nb_pallet = fields.Integer('Number of palet')
    number_of_packages = fields.Integer(string='Nb packages')
    


    def button_print_chronopost(self):
        res = {}
        context = {}

        for picking in self:
            if picking.carrier_id.edi_chronopost:
                if picking.edi_state == 'todo':
                    # Get content
                    picking_content = ''
                    carrier_content = picking.carrier_order_id.chronopost_content
                    for line in carrier_content.split('\n'):
                        if picking.name in line:
                            picking_content = line
                            break
                    # Write file
                    file_name = 'CHRONOPOST_%s.csv' % (picking.name)
                    chrono_dir = os.listdir(CHRONO_MNT)
                    if 'SCRUT' in chrono_dir:
                        chrono_file = open(CHRONO_MNT + '/SCRUT/' + file_name, 'w')
                        picking_content = "".join(filter(lambda c: ord(c) < 128, picking_content))
                        chrono_file.write(picking_content)
                        chrono_file.close()
                        picking.write({'edi_state': 'progress'})
                    else:
                        picking.write({'edi_state': 'error'})

    def update_edi_state(self):
        res = {}
        context = {}

        for picking in self:
            #check mount
            #check file_name
            if picking.carrier_id.edi_chronopost:

                if not picking.edi_state or picking.edi_state == 'none':
                    picking.write({'edi_state': 'todo'})
                elif picking.edi_state == 'progress':
                    chrono_dir = os.listdir(CHRONO_MNT)
                    if not chrono_dir:
                        # Not connected
                        picking.write({'edi_state': 'error'})

                    elif 'LOG' in chrono_dir:
                        log_files = os.walk(CHRONO_MNT + '/LOG')
                        for root, dirs, file_names in log_files:
                            for file_name in file_names:
                                if picking.name in file_name:
                                    picking.write({'edi_state': 'done'})
                                    break

                        if picking.edi_state != 'done':
                            log_error = os.walk(CHRONO_MNT + '/ERROR')
                            for root, dirs, file_names in log_error:
                                for file_name in file_names:
                                    if picking.name in file_name:
                                        picking.write({'edi_state': 'error'})
                                        break
            else:
                picking.write({'edi_state': 'none'})

            if picking.carrier_order_id:
                if picking.carrier_order_id.edi_done:
                    #picking.edi_state = 'done'
                    pass
        return True

    def check_carrier(self):
        context = {}
        carrier_obj = self.env['delivery.carrier.order']
        carrier_ids = []
        for picking in self:
            if picking.id not in carrier_ids:
                carrier_ids.append(picking.id)
        carrier_obj.check_state(carrier_ids)

        return True

    def button_action_send(self):
        context =  {}
        context['active_ids'] = ids

        mail_obj = self.env['mail.mail']
        template_obj = self.env['email.template']
        model_obj = self.env['ir.model']
        attachement_obj = self.env['ir.attachment']
        invoice_obj = self.env['account.invoice']
        message_ids = []

        for picking in self:

            email_contact_id = False
            email_invoice = False
            email_picking = False
            email_picking2 = False

            if picking.partner_id:
                partner = picking.partner_id
                if partner and partner.email_partner_id:
                    partner = picking.partner_id
                elif partner and partner.parent_id and partner.parent_id.email_partner_id:
                    partner = partner.parent_id
                elif partner and partner.parent_id and partner.parent_id.parent_id and partner.parent_id.parent_id.email_partner_id:
                    partner = partner.parent_id.parent_id
                else:
                    partner = False
            else:
                return True

            if partner:
                email_contact_id = partner.email_partner_id or False
                email_invoice = partner.email_invoice
                email_picking = partner.email_picking
                email_picking2 = partner.email_picking2

                if email_contact_id and (email_invoice or email_picking or email_picking2):
                    #make email body
                    invoice_ids = invoice_obj.search([('picking_id', '=', picking.id)])
                    template_ids = template_obj.search([('model', '=', 'account.invoice')])
                    model_ids = model_obj.search([('model', '=', 'account.invoice')])

                    if invoice_ids and template_ids:
                        compose_ctx = {
                            'template_id': template_ids[0],
                            'active_id': invoice_ids[0],
                            'active_ids': [invoice_ids[0]],
                            'active_model_id': model_ids[0],
                            'lang': partner.lang or 'fr_FR',
                            'tz': context.get('tz', 'Europe/Paris'),
                            }

                        template_vals = {
                            'template_id': template_ids[0],
                            'model_id': model_ids[0],
                            'lang': partner.lang or 'fr_FR',
                            }

                        compose_id = self.env['email_template.preview'].create(template_vals)
                        preview_vals = self.env['email_template.preview'].on_change_res_id(compose_id, invoice_ids[0],
                                context=compose_ctx)['value']
                        #print "=====compose_id=====", partner.name, email_contact_id.email,  '\n', preview_vals

                        message_vals = {}
                        attachment_ids = []
                        if preview_vals.get('body_html'):
                            message_vals['body_html'] = preview_vals.get('body_html')
                        message_vals['email_to'] = email_contact_id.email or picking.partner_id.email or ''
                        message_vals['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        message_vals['reply_to'] = partner.user_id and partner.user_id.email or picking.company_id.email
                        message_vals['subject'] = preview_vals.get('subject', 'Hennart Delivery')
                        message_vals['model'] = "account.invoice"
                        message_vals['res_id'] = invoice_ids[0]
                        message_vals['partner_ids'] = [(6, 0, [partner.id])]
                        message_vals['author_id'] = partner.user_id and partner.user_id.partner_id.id or SUPERUSER_ID
                        message_vals['type'] = "email"
                        message_vals['email_from'] = partner.user_id and partner.user_id.email or picking.company_id.email

                        #Attachment pdf invoice
                        pdf_context = {'lang': partner.lang or 'fr_FR', 'tz': context.get('tz', 'Europe/Paris')}

                        if email_invoice:
                            invoice = invoice_obj.browse(invoice_ids[0])
                            attachment_vals = {}
                            attachment_vals['res_model'] = "account.invoice"
                            attachment_vals['res_id'] = invoice.id
                            attachment_vals['res_name'] = 'hennart_' + invoice.number + '.pdf'
                            attachment_vals['name'] = 'hennart_' + invoice.number + '.pdf'
                            attachment_vals['type'] = 'binary'
                            attachment_vals['file_type'] = 'application/pdf'
                            attachment_vals['user_id'] = partner.user_id and partner.user_id.id or SUPERUSER_ID
                            attachment_vals['partner_id'] = partner.id or False

                            service = netsvc.LocalService('report.account.invoice.invoice1')
                            (result, format) = service.create([invoice.id], {'model': "account.invoice"})
                            attachment_vals['db_datas'] = base64.b64encode(result)
                            attachment_vals['datas_fname'] = 'hennart_' + invoice.number + '.pdf'
                            attachement_pdf_id = attachement_obj.create(attachment_vals)
                            attachment_ids.append(attachement_pdf_id)

                        if email_picking2:
                            invoice = invoice_obj.browse(invoice_ids[0])
                            attachment_vals = {}
                            attachment_vals['res_model'] = "account.invoice"
                            attachment_vals['res_id'] = invoice.id
                            attachment_vals['res_name'] = 'hennart_' + invoice.name + '_2.pdf'
                            attachment_vals['name'] = 'hennart_' + invoice.name + '_2.pdf'
                            attachment_vals['type'] = 'binary'
                            attachment_vals['file_type'] = 'application/pdf'
                            attachment_vals['user_id'] = partner.user_id and partner.user_id.id or SUPERUSER_ID
                            attachment_vals['partner_id'] = partner.id or False

                            service = netsvc.LocalService('report.account.invoice.invoice2')
                            (result, format) = service.create([invoice.id], {'model': "account.invoice"})
                            attachment_vals['db_datas'] = base64.b64encode(result)
                            attachment_vals['datas_fname'] = 'hennart_' + invoice.name + '_2.pdf'
                            attachement_pdf_id = attachement_obj.create(attachment_vals)
                            attachment_ids.append(attachement_pdf_id)

                        if email_picking:
                            attachment_vals = {}
                            attachment_vals['res_model'] = "stock.picking"
                            attachment_vals['res_id'] = picking.id
                            attachment_vals['res_name'] = 'hennart_' + picking.name + '.pdf'
                            attachment_vals['name'] = 'hennart_' + picking.name + '.pdf'
                            attachment_vals['type'] = 'binary'
                            attachment_vals['file_type'] = 'application/pdf'
                            attachment_vals['user_id'] = partner.user_id and partner.user_id.id or SUPERUSER_ID
                            attachment_vals['partner_id'] = picking.partner_id.id or False

                            service = netsvc.LocalService('report.stock.picking')
                            (result, format) = service.create([picking.id], {'model': "stock.picking"})
                            attachment_vals['db_datas'] = base64.b64encode(result)
                            attachment_vals['datas_fname'] = 'hennart_' + picking.name + '.pdf'
                            attachement_pdf_id = attachement_obj.create(attachment_vals)
                            attachment_ids.append(attachement_pdf_id)

                        if attachment_ids:
                            message_vals['attachment_ids'] = [(6, 0, attachment_ids)]
                        message_id = mail_obj.create(message_vals)
                        message_ids.append(message_id)

        if message_ids:
            mail_obj.send(message_ids)

        return True
