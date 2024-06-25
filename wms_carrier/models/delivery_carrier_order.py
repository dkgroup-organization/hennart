

from odoo import models, fields ,api, _, SUPERUSER_ID
import time
import datetime
import unicodedata
import time
import datetime
from dateutil.relativedelta import relativedelta
import pytz
import pysftp
import base64
from odoo.exceptions import MissingError, UserError, ValidationError


class delivery_carrier_order(models.Model):

    _name = "delivery.carrier.order"
    _description = "Carrier Order"
    _inherit = ['mail.thread']

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
    save_as = fields.Binary(compute="_get_content", string='save as')
    save_name = fields.Char(compute="_update_info", size=32, string='save as',)
    content = fields.Text(compute="_csv_content", string='Content of export')

    sscc_save_as = fields.Binary(compute="_get_content_sscc", string='save as')
    sscc_save_name = fields.Char(compute="_update_info",  size=32, string='save as')
    sscc_content = fields.Text(compute="_csv_content_sscc3", string='Content of export')

    chronopost_save_as = fields.Binary(compute="_get_content_chronopost", string='save as')
    chronopost_save_name = fields.Char(compute="_update_info", size=62, string='save as')
    chronopost_content = fields.Text(compute="_csv_content_chronopost", string='Content of export')


    def _update_info(self):
        
        date_now = time.strftime('%Y-%m-%d')
        for carrier_order in self:
          if carrier_order:
            if carrier_order.date_expected:
               testoo = carrier_order.date_expected.strftime('%Y-%m-%d')
            else: 
                testoo = False
            order_date = testoo or date_now
            # order_date = order_date2.strftime('%Y-%m-%d')
            nagel_name = 'DZV_HENNART____CALTMS_IMP_AUFTRAEGE_'
            nagel_counter = str(order_date).replace('-', '')
            carrier_order.save_name = carrier_order.name.replace(' ', '_') + '_' + str(order_date)+ '.csv'
            carrier_order.sscc_save_name=nagel_name + nagel_counter + '.DFD'
            carrier_order.chronopost_save_name=carrier_order.name.replace(' ', '_') + '_' + str(order_date) + '_chronopost.csv'
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
                    
    def _get_content(self):
        for obj_current in self:
            obj_current.save_as = False
            mm = ""
            if obj_current.content:
                obj_current.save_as = base64.encodebytes((obj_current.content).encode('utf-8'))
            else:
                obj_current.save_as = base64.encodebytes(mm.encode('utf-8'))


    def _csv_content(self):
        fields_to_export = [
            ('scheduled_date', 'date_expedition', 'date'),
            ('date_delivered', 'date_livraison', 'date'),
            ('partner_id.ref', 'code_destinataire', 'char'),
            ('partner_id.name', 'nom_destinataire', 'char'),
            ('partner_id.street', 'rue_destinataire', 'char'),
            ('partner_id.street2', 'rue2_destinataire', 'char'),
            ('partner_id.zip', 'cp_destinataire', 'char'),
            ('partner_id.city', 'ville_destinataire', 'char'),
            ('note', 'observation', 'char'),
            ('nb_pallet', 'nb_palette', 'integer'),
            ('nb_container', 'nb_container', 'integer'),
            ('number_of_packages', 'nb_colis', 'integer'),
            ('weight', 'poids', 'float'),

            ]

        csv_text = ''
        csv_separator = ';'
        csv_return = '\r\n'
        for field in fields_to_export:
            csv_text += field[1] + csv_separator
        csv_text = csv_text[:-1] + csv_return

        for obj_current in self:
            obj_current.content = ""

            for line in obj_current.picking_ids:
                for field in fields_to_export:
                    try:
                        field_value = eval('line.' + field[0])

                        #format
                        if field[2] == 'date':
                            field_value2 = str(field_value)
                            field_value = field_value2[8:10] + field_value2[5:7] + field_value2[0:4]
                        elif field[2] == 'char':
                            field_value = unicodedata.normalize('NFKD', field_value).encode('ascii', 'ignore').decode()
                            field_value = field_value.replace('\n', ' ')
                            field_value = field_value.replace(';', ' ')
                            field_value = field_value.replace('\r\n', ' ')
                            
                        else:
                           field_value = '%s' % (field_value)

                    except:
                        field_value = ''

                    #Exception, ref on parent partner
                    if field[0] == 'partner_id.ref' :
                        field_value = line.partner_id.ref
                        if not field_value :
                           if line.partner_id and line.partner_id.parent_id:
                              field_value = line.partner_id.parent_id.ref or ''

                    if field[0] == 'note' :
                        field_value = obj_current.note
                
                    #Exception, date delivered always j+1


                    if field[0] == 'date_delivered':
                        next_date = line.scheduled_date + relativedelta(days=1)
                        field_value = next_date.strftime('%d%m%Y')
                    if field[0] == 'scheduled_date':
                        next_date = line.scheduled_date
                        field_value = next_date.strftime('%d%m%Y')
                    if field_value != '' and field_value != False and field_value != 'False':

                       field_value = field_value.replace(csv_return, ' ').replace(csv_separator, ' ')
                       csv_text += '%s%s' % (field_value, csv_separator)
                    else:
                        csv_text += '%s' % (csv_separator)

                csv_text = csv_text[:-1] + csv_return
                obj_current.content = csv_text[:-1]

    def check_state(self):
        for order in self:
            state_order = order.state
            if order.state not in ['cancel', 'done']:
                states = []
                for picking in order.picking_ids:
                    if picking.state not in states:
                        states.append(picking.state)
                if "draft" in states:
                    state_order = 'confirmed'
                elif 'confirmed' in states:
                    state_order= 'confirmed'
                elif 'assigned' in states:
                    state_order = 'assigned'
                elif 'done' in states:
                    state_order = 'done'
                elif 'cancel' in states:
                    state_order = 'cancel'
            if order.state != state_order:
               order.write({'state': state_order})
        return order

    
    def button_action_done(self):
        
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

    def _csv_content_sscc3(self):
       
        csv_return = '\r\n'

        def format_date(field_value):
            if field_value:
                field_value2 = str(field_value)
                date = field_value2[8:10] + field_value2[5:7] + field_value2[0:4]
            else:
                date = ''
            return date

        def format_text(field_value):

            text = ''
            if field_value:
                field_value = field_value.replace(';', ' ')
                field_value = field_value.replace('\r\n', ' ')
                field_value = field_value.replace('\n', ' ')
                # field_value = ascii(field_value) 
                field_value = unicodedata.normalize('NFKD', field_value).encode('ascii', 'ignore').decode()
                text = "%s" % (field_value)
            return text

        #group data
        for transport in self:
            transport.sscc_content = ""
            data = {}
            listoo = []
            for picking in transport.picking_ids:
                if picking.partner_id:
                    partner_id = picking.partner_id.id
                    #create one record by partner
                    if partner_id not in listoo:
                        data = {'nb_palette': 0, 'nb_container': 0, 'nb_colis': 0, 'poids': 0.0, 'order': '', 'sscc': ''}
                        #date
                        data['date_expedition'] = format_date(picking.scheduled_date)

                        if picking.date_delivered:
                            data['date_livraison'] = format_date(picking.date_delivered)
                        else:
                            date_delivered = datetime.datetime.strptime(str(picking.scheduled_date), '%Y-%m-%d %H:%M:%S') + relativedelta(days=1)
                            data['date_livraison'] = date_delivered.strftime('%d%m%Y')

                        #address
                        data['nom_destinataire'] = format_text(picking.partner_id.name)
                        data['rue_destinataire'] = format_text(picking.partner_id.street)
                        data['rue2_destinataire'] = format_text(picking.partner_id.street2)
                        data['cp_destinataire'] = format_text(picking.partner_id.zip)
                        data['ville_destinataire'] = format_text(picking.partner_id.city)
                        data['observation'] = format_text(picking.note)

                        #code partner
                        if picking.partner_id.ref:
                            ref = picking.partner_id.ref
                        elif picking.partner_id.parent_id.ref:
                            ref = picking.partner_id.parent_id.ref
                        else:
                            ref = ''
                        data['code_destinataire'] = format_text(ref)

                        #Code country
                        if picking.partner_id.country_id:
                            country_code = picking.partner_id.country_id.code
                        elif picking.partner_id.parent_id.country_id:
                            country_code = picking.partner_id.parent_id.country_id.code
                        else:
                            country_code = 'FR'
                        data['code_pays'] = format_text(country_code)

                        # Routing zone specific to Nagel carrier
                        if country_code in ['FR', 'NL', 'GB']:
                            routing_code = 'F59'
                        elif country_code in ['DE', 'AT']:
                            routing_code = 'D66'
                        else:
                            routing_code = ''

                        data['branch'] = routing_code

                        #delivery zone
                        if picking.partner_id.carrier_zone:
                            carrier_zone = picking.partner_id.carrier_zone
                        elif picking.partner_id.parent_id and picking.partner_id.parent_id.carrier_zone:
                            carrier_zone = picking.partner_id.parent_id.carrier_zone
                        else:
                          carrier_zone = ''
                        data['zone_transport'] = format_text(carrier_zone)
                        listoo.append(partner_id)




                    #Cumulative data
                    data['nb_palette'] += picking.nb_pallet or 0
                    data['nb_container'] += picking.nb_container or 0
                    data['nb_colis'] += picking.number_of_packages or 0
                    data['poids'] += picking.weight or 0.0

                    #order
                    if not data['order']:
                        data['order'] = picking.name
                    else:
                        data['order'] += ',' + picking.name

                    #SSCC
                    for sscc in picking.sscc_line_ids:
                        if data['sscc']:
                            data['sscc'] += ','
                        data['sscc'] += sscc.name
                    
        header = "date_expedition;date_livraison;code_destinataire;nom_destinataire;rue_destinataire;rue2_destinataire;"
        header += "cp_destinataire;ville_destinataire;observation;nb_palette;nb_container;nb_colis;poids;order;branch;zone_transport;sscc;code_pays;"
        header += csv_return

        
        transport.sscc_content  = "%s" % (header)

        for transport_id in self:
            
            for partner_id in listoo:
                line = ''
                for field_name in header.split(';'):
                    if field_name == csv_return:
                        pass
                    else:
                        line += "%s;" % (data[field_name])
                if line:
                    line += csv_return
                #add line
                transport_id.sscc_content = transport_id.sscc_content + line

    def _get_content_sscc(self):
        for obj_current in self:
            mm = ""
            if obj_current.sscc_content:
                obj_current.sscc_save_as = base64.encodebytes((obj_current.sscc_content).encode('utf-8'))
            else:
                obj_current.sscc_save_as = base64.encodebytes(mm.encode('utf-8'))
    def _csv_content_chronopost(self):
        coef_brut_net = 1.1

        format_chronopost = [u"R\xe9f\xe9rence destinataire", u"Nom ou Raison sociale", u"Suite Nom ou Suite Raison sociale ou Pr\xe9nom ou Contact",
             u"Suite Nom 2 ou Suite Raison sociale 2 ou Pr\xe9nom ou Contact", u"Adresse destinataire", u"Adresse destinataire suite",
             u"Digicode / Etage / Interphone", u"Code Postal destinataire", u"Ville Destinataire", u"Code Pays destinataire",
             u"T\xe9l\xe9phone destinataire", u"Email destinataire", u"R\xe9f\xe9rence envoi", u"Code barres client", u"Produit",
             u"Compte", u"Sous-compte", u"Valeur assur\xe9e", u"Valeur douane", u"Document / marchandise", u"Description du contenu", u"Livraison le samedi",
             u"Identifiant Relais", u"Poids", u"Largueur", u"Longueur", u"Hauteur", u"Avertir destinataire", u"Nombre de colis", u"date d'envoi",
             u"A int\xe9grer", u"Avertir exp\xe9diteur", u"DLC", u"D\xe9but de cr\xe9neau", u"Fin de cr\xe9neau", u"Code tarifaire",
             u"Code service"]

        csv_header = ''
        csv_separator = ';'
        csv_return = '\n'

        #create the CSV Header of picking
        for field in format_chronopost:
            csv_header += field + csv_separator
        csv_header = csv_header[:-1] + csv_return
        #Chronopost don't need header
        csv_header = ''

        #extract picking info
        for carrier in self:

            carrier.chronopost_content  = csv_header

            for picking in carrier.picking_ids:

                field_value = {
                    u"R\xe9f\xe9rence destinataire": picking.name,
                    u"Nom ou Raison sociale": picking.partner_id.name or '',
                    u"Suite Nom 2 ou Suite Raison sociale 2 ou Pr\xe9nom ou Contact": '',
                    u"Adresse destinataire": picking.partner_id.street or '',
                    u"Adresse destinataire suite": picking.partner_id.street2 or '',
                    u"Code Postal destinataire": picking.partner_id.zip or '',
                    u"Ville Destinataire": picking.partner_id.city or '',
                    u"Code Pays destinataire": picking.partner_id.country_id and picking.partner_id.country_id.code or 'FR',
                    u"T\xe9l\xe9phone destinataire": picking.partner_id.phone or '',
                    u"Email destinataire": picking.partner_id.email or '',
                    u"R\xe9f\xe9rence envoi": picking.name or '',
                    u"A int\xe9grer": 'Y',
                    }

                #Code country
                if picking.partner_id.country_id:
                    country_code = picking.partner_id.country_id.code
                elif picking.partner_id.parent_id.country_id:
                    country_code = picking.partner_id.parent_id.country_id.code
                else:
                    country_code = 'FR'

                field_value['Code Pays destinataire'] = country_code or 'FR'

                #telephone
                if not field_value[u'T\xe9l\xe9phone destinataire']:
                    if picking.partner_id.parent_id and picking.partner_id.parent_id.phone:
                        field_value[u'T\xe9l\xe9phone destinataire'] = picking.partner_id.parent_id.phone
                #email
                if not field_value['Email destinataire']:
                    if picking.partner_id.parent_id and picking.partner_id.parent_id.email:
                        field_value['Email destinataire'] = picking.partner_id.parent_id.email
                if ';' in field_value['Email destinataire']:
                    double_email = field_value['Email destinataire'].split(';')
                    field_value['Email destinataire'] = double_email[0]

                #date
                if carrier.date_expected:
                    date_expected = datetime.datetime.strptime(str(carrier.date_expected), '%Y-%m-%d %H:%M:%S')
                    date_dlc = date_expected + datetime.timedelta(days=5)
                    field_value["date d'envoi"] = date_expected.strftime('%d/%m/%Y')
                    field_value["DLC"] = date_dlc.strftime('%d/%m/%Y')

                if field_value['Email destinataire']:
                    field_value['Avertir destinataire'] = '2'
                else:
                    field_value['Avertir destinataire'] = 'N'

                nb_colis = picking.nb_container + picking.nb_pallet
                field_value['Nombre de colis'] = "%d" % (int(nb_colis))

                weight = picking.weight
                field_value['Poids'] = "%1.2f" % (weight * coef_brut_net)

                csv_picking = ''
                for field_header in format_chronopost:
                    if field_value.get(field_header):
                        ascii_value = "%s" % (field_value[field_header])
                        ascii_value = ascii_value.replace(csv_separator, ' ')
                        ascii_value = ascii_value.replace(csv_return, ' ')
                        csv_picking += ascii_value + csv_separator
                    else:
                        csv_picking += csv_separator

                csv_picking = csv_picking[:-1] + csv_return

                carrier.chronopost_content = csv_header+ csv_picking
                csv_header = carrier.chronopost_content

        

    def _get_content_chronopost(self):

        for obj_current in self:
            mm = ""
            if obj_current.chronopost_content:
                obj_current.chronopost_save_as = base64.encodebytes((obj_current.chronopost_content).encode('utf-8'))
            else:
                obj_current.chronopost_save_as = base64.encodebytes(mm.encode('utf-8'))

    def button_action_send(self):

        message = self.env['mail.mail']
        template_obj = self.env['mail.template']
        model_obj = self.env['ir.model']

        attachement = self.env['ir.attachment']
        invoice_obj = self.env['account.move']
        report = self.env['ir.actions.report']
        report_ids = report.search([('model', '=', "delivery.carrier.order")])
        report_id = report_ids and report_ids[0] or False
        report_service = report_id and 'report.' + report.browse(report_id.id).report_name or ''

        for carrier_order in self:
            if carrier_order.edi_done or not carrier_order.carrier_id or not carrier_order.carrier_id.edi_partner_id:
                continue

            message_vals = {}
            attachment_ids = []
            if carrier_order.carrier_id.edi_body:
                message_vals['body'] = carrier_order.carrier_id.edi_body
            if carrier_order.carrier_id.edi_partner_id:
                message_vals['email_to'] = carrier_order.carrier_id.edi_partner_id.email or ''
            message_vals['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
            message_vals['reply_to'] = carrier_order.warehouse_id.company_id.email
            message_vals['subject'] = carrier_order.carrier_id.edi_subject or ''
            if not carrier_order.carrier_id.edi_subject:
                message_vals['record_name'] = ''
            message_vals['model'] = "delivery.carrier.order"
            message_vals['res_id'] = carrier_order.id
            #mail_message_id
            #message_id
            if carrier_order.carrier_id.edi_partner_id:
                message_vals['partner_ids'] = [(6, 0, [carrier_order.carrier_id.edi_partner_id.id])]

            message_vals['author_id'] = SUPERUSER_ID
            # message_vals['type'] = "email"
            message_vals['email_from'] = carrier_order.warehouse_id.company_id.email or ''

            #Attachment sscc csv
            if carrier_order.carrier_id.edi_sscc_csv:
                attachment_vals = {}
                attachment_vals['res_model'] = "delivery.carrier.order"
                attachment_vals['res_id'] = carrier_order.id
                attachment_vals['res_name'] = carrier_order.sscc_save_name or '?'
                attachment_vals['name'] = carrier_order.sscc_save_name or '?'
                attachment_vals['type'] = 'binary'
                if carrier_order.content:
                    attachment_vals['datas'] = base64.encodebytes(carrier_order.sscc_content.encode('utf-8'))
                    attachment_vals['name'] = carrier_order.sscc_save_name
                else:
                    attachment_vals['datas'] = base64.encodebytes("")

                attachement_csv_id = attachement.create(attachment_vals)
                attachment_ids.append(attachement_csv_id.id)

            #Attachment csv
            if carrier_order.carrier_id.edi_csv:
                attachment_vals = {}
                attachment_vals['res_model'] = "delivery.carrier.order"
                attachment_vals['res_id'] = carrier_order.id
                attachment_vals['res_name'] = carrier_order.save_name or '?'
                attachment_vals['name'] = carrier_order.save_name or '?'
                attachment_vals['type'] = 'binary'
                if carrier_order.content:
                    attachment_vals['datas'] = base64.encodebytes(carrier_order.content.encode('utf-8'))
                    attachment_vals['name'] = carrier_order.save_name
                else:
                    attachment_vals['datas'] = base64.encodebytes("")

                attachement_csv_id = attachement.create(attachment_vals)
                attachment_ids.append(attachement_csv_id.id)

            #Attachment pdf
            if carrier_order.carrier_id.edi_pdf:
                generated_report = self.env['ir.actions.report']._render_qweb_pdf("wms_carrier.action_report_delivery_carrier_order", carrier_order.id)
                # generated_report = carrier_report_id._render_qweb_pdf(carrier_order.id)
                data_record = base64.b64encode(generated_report[0])
                ir_values = {
                'name': carrier_order.save_name.replace('.csv', '.pdf') or '?',
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record,
                'mimetype': 'application/pdf',
                'res_model': 'delivery.carrier.order',
                'res_id': carrier_order.id,
                }
                attachement_pdf_id = attachement.create(ir_values)
                attachment_ids.append(attachement_pdf_id.id)

            if attachment_ids:
                message_vals['attachment_ids'] = [(6, 0, attachment_ids)]

            #Send
            message_id = message.create(message_vals)
            message.send(message_id.id)
            carrier_order.write({'edi_done': True})

        self.button_send_sftp()
        return True

    def button_send_sftp(self):
        for order in self:

            # connection data
            hostname = order.carrier_id.sftp_server
            username = order.carrier_id.sftp_user
            password = order.carrier_id.sftp_password
            sftp_dir = order.carrier_id.sftp_dir
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            # connection
            if hostname and username and password:
               
                try:
                    edi_sftp = pysftp.Connection(hostname, username=username, password=password, cnopts=cnopts)
                except:
                    edi_sftp = False

                if not edi_sftp:
                    raise UserError(_('SFTP Error!'), _('The connection to SFTP server is in error.'))

                if order.carrier_id.edi_sscc_csv:
                    datas_fname = order.sscc_save_name
                    db_datas = order.sscc_content or ""
                elif order.carrier_id.sscc_csv:
                    datas_fname = order.save_name
                    db_datas = order.content or ""
                else:
                    datas_fname = 'hennart_edi_test.txt'
                    db_datas = ""

                file_edi_name = '/tmp/' + datas_fname
                file_edi = open(file_edi_name, 'w')
                file_edi.write(db_datas)
                file_edi.close()

                if sftp_dir:
                    edi_sftp.chdir(sftp_dir)
                edi_sftp.put(file_edi_name)

        return True
