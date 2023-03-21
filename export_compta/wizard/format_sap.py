# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import codecs
import base64
import logging
import locale
import unicodedata

logger = logging.getLogger(__name__)


def remove_accents(input_str):
    only_ascii = unicodedata.normalize('NFD', input_str).encode('ascii', 'ignore')
    if type(only_ascii) == bytes:
        return only_ascii.decode()
    else:
        return only_ascii


def txt_cleanup(text):
    if text:
        text = remove_accents(text)
        text = text.replace('\"', ' ')
        text = text.replace('\n', ' ')
        text = text.replace(';', ' ')
        text = text.replace('%', ' ')
        text = text.replace('"', ' ')
        text = text.replace('   ', ' ')
        text = text.replace('  ', ' ')
        text = text.strip()
        return text
    else:
        return ''


def format_line(file_data, widths):
    "return formated ligne"
    line_of_file = ''.encode('ascii')
    for field_value, width in zip(file_data, widths):
        if len(field_value) > width:
            field_value = field_value[:width]
        if len(line_of_file):
            line_of_file += ';'.encode('ascii')
        line_of_file += ('%s' % (field_value.ljust(width))).encode('ascii')
    line_of_file += "\n".encode('ascii')
    return line_of_file


def txt_cleanup_price(text):
    text = str(text)
    if text:
        text = text.replace('\"', ' ')
        text = text.replace('\n', ' ')
        return text
    else:
        return ''


class ExportMoveSAP(models.TransientModel):
    _name = "export.move.sap"
    _description = "Export data Move & Move line SAP"

    name = fields.Char('Name', size=32, default='')
    journal_type = fields.Selection([
            ('sale', 'Sales'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
            ('all', 'all'),
        ],
        help="Select 'Sale' for customer invoices journals.\n"\
        "Select 'Purchase' for vendor bills journals.\n"\
        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
        "Select 'General' for miscellaneous operations journals.")
    date_from = fields.Date('Date start')
    date_to = fields.Date('Date end')
    state = fields.Selection([('confirm', 'confirm'), ('get', 'get')], default='confirm')
    message = fields.Text('Message', readonly=True)
    message_ml = fields.Text('Message', readonly=True)
    attachment_id = fields.Many2one('ir.attachment', string="Attachment moves")
    attachment_name = fields.Char(related='attachment_id.name', readonly=True)
    attachment_datas = fields.Binary(related='attachment_id.datas', readonly=True)
    attachment_ml_id = fields.Many2one('ir.attachment', string="Attachment move lines")
    attachment_ml_name = fields.Char(related='attachment_ml_id.name', readonly=True)
    attachment_ml_datas = fields.Binary(related='attachment_ml_id.datas', readonly=True)

    @api.model
    def get_account_sap(self, move_line):
        "Return SAP codification"
        account_sap = '/'

        if move_line.account_id.user_type_id.type not in ['receivable', 'payable']:
            account_sap = move_line.account_id.export_code or move_line.account_id.code
        else:
            if move_line.partner_id.export_code:
                account_sap = move_line.partner_id.export_code
            elif move_line.partner_id.parent_id.export_code:
                account_sap = move_line.partner_id.parent_id.export_code
            elif move_line.move_id.channel_id.export_code:
                account_sap = move_line.move_id.channel_id.export_code
            elif move_line.partner_id.channel_id.export_code:
                account_sap = move_line.partner_id.channel_id.export_code
            else:
                raise ValidationError(_("There is no Partner code SAP (move.line.id: %d): %s") % (move_line.id, move_line.partner_id.name))

        return account_sap

    @api.model
    def get_account_key_sap(self, move_line):
        "Return SAP codification"
        """
        Clé de Compte	Type de compte	Débit / Crédit	Libellé
        01	C	D	Facture
        02	C	D	Annulat. avoir
        03	C	D	Frais
        04	C	D	Autre créance
        05	C	D	Décaissement
        06	C	D	Ecart de paiement
        07	C	D	Autre compensation
        08	C	D	Compens. paiement
        09	C	D	CGS client/débit
        0A	C	D	CH Facture client
        0B	C	D	CH Annul.AvoirClient
        0C	C	D	CH Compensat. client
        0X	C	D	CH Compens. fourn.
        0Y	C	D	CH Avoir fournisseur
        0Z	C	D	CH Annul.fact.client
        11	C	C	Avoir
        12	C	C	Annulation facture
        13	C	C	C-passation frais
        14	C	C	Autre dettes
        15	C	C	Encaissement
        16	C	C	Ecart de paiement
        17	C	C	Autre compensation
        18	C	C	Compens. paiement
        19	C	C	CGS client/crédit
        1A	C	C	CH Annul.fact.client
        1B	C	C	CH Avoir client
        1C	C	C	CH Avoir client
        1X	C	C	CH Compens. fourn.
        1Y	C	C	CH Annul.AvoirClient
        1Z	C	C	CH Facture fourniss.
        21	F	D	Avoir
        22	F	D	Annulation facture
        24	F	D	Autre créance
        25	F	D	Décaissement
        26	F	D	Ecart de paiement
        27	F	D	Compensation
        28	F	D	Compens. paiement
        29	F	D	CGS fournisseur/déb.
        31	F	C	Facture
        32	F	C	Annulat. avoir
        34	F	C	Autres dettes
        35	F	C	Encaissement
        36	F	C	Ecart de paiement
        37	F	C	Autre compensation
        38	F	C	Compens. paiement
        39	F	C	CGS fourniss. crédit
        40	G	D	Ecriture débit
        50	G	C	Ecriture crédit
        70	I	D	Immo. débit
        75	I	C	Immo. crédit
        80	G	D	Saisie stock initial
        81	G	D	Coûts
        83	G	D	Différence de prix
        84	G	D	Consommation
        85	G	D	Variation de stockKR
        86	G	D	Débit EM/EF
        89	A	D	Entrée en stock
        90	G	C	Saisie stock initial
        91	G	C	Coûts
        93	G	C	Différence de prix
        94	G	C	Consommation
        95	G	C	Variation de stock
        96	G	C	Crédit EM/EF
        99	A	C	Sortie de stock
        """
        account_key_sap = '/'
        map_key_credit = {'DR': '12', 'DG': '11', 'KR': '31', 'KG': '32', 'DZ': '15', 'KZ': '35', 'SA': '50'}
        map_key_debit = {'DR': '01', 'DG': '02', 'KR': '22', 'KG': '21', 'DZ': '05', 'KZ': '25', 'SA': '40'}

        if move_line.account_id.user_type_id.type not in ['receivable', 'payable']:
            if move_line.credit:
                account_key_sap = '50'
            elif move_line.debit:
                account_key_sap = '40'
        else:
            move_key_sap = self.get_move_key_sap(move_line.move_id)

            if move_line.credit and move_key_sap:
                account_key_sap = map_key_credit.get(move_key_sap, '/')
            elif move_line.debit and move_key_sap:
                account_key_sap = map_key_debit.get(move_key_sap, '/')
        if account_key_sap == '/':
            raise ValidationError(_("There is no account key SAP (move.id: %d) when trying to export") % move_line.move_id.id)
        return account_key_sap

    @api.model
    def get_move_key_sap(self, move):
        """Return SAP codification
        Type de pièce	Libellé
        AA	Ecriture immo.
        AB	Production Immobilis
        AF	Ecritures amort.
        AG	Ecritures Périod Amo
        AM	Ecriture immo Manuel
        AN	Z_Ecriture immo.net
        CH	Z_Débouclage contrat
        CO	Rapprochemt FICO
        DA	Pièce client
        DG	Note crédit client
        DL	Lettrage client
        DR	Facture client
        DZ	Paiement client
        EU	Z_Euro Ecart arrondi
        EX	Z_Numéro externe
        IF	Pièces IFRS
        KA	Pièce fournisseur
        KG	Note crédit fourn.
        KL	Lettrage fournisseur
        KN	Z_Net fournisseurs
        KP	Gestion compte EMEF
        KR	Facture fournisseur
        KZ	Paiement fournisseur
        ML	Z_ML Décompte
        PR	Modification de prix
        RA	Réduction facture MM
        RB	Z_Prov.créanc.dout.
        RC	Facture MM Consignat
        RE	Facture MM
        RF	RFA MM
        RN	Z_Facture (net)
        RP	Factu Int/Retard LME
        RQ	Avoir Int/Retard LME
        RV	Facture SD
        RW	Avoir SD
        RX	Provision SD
        RY	Avoir RFA, Coop
        SA	Pièce compte général
        SB	OD reversal
        SC	Interface paie
        SD	Moulinette
        SE	Extourne BanqueDR
        SF	Pièces RAN FEC
        SI	OD reversal-Interco-
        SK	Z_Pièce de caisse
        SU	Z_Pièce imput.ultér.
        UE	Z_Reprise données
        WA	EntréeSortie Marchan
        WE	Entrée marchandises
        WI	Pièce d'inventaire
        WL	Sortie march./Livr.
        WN	Z_Entrée march nette
        X1	Pièce périodique
        ZA	Pièce clt Repris PNS
        ZF	Fact clt Repris PNS
        ZG	Avoir Clt Repris PNS
        ZI	Ecritures IFRS
        ZM	Paiement Manuel
        ZO	Paiement auto Prélvt
        ZP	Paiement auto Virt
        ZQ	Paiement auto Traite
        ZR	Z_rapprochement banc
        ZS	Z_Paiement chèque
        ZV	Z_Compens. paiement
        ZZ	Reprise Bal + EffetsKZ
        """
        move_key_sap = False
        if move.journal_id.type == 'sale':
            if move.move_type == 'out_invoice':
                # facture client
                move_key_sap = 'DR'
            elif move.move_type == 'out_refund':
                # Note de credit client
                move_key_sap = 'DG'
        elif move.journal_id.type == 'purchase':
            if move.move_type == 'in_invoice':
                # facture fournisseur
                move_key_sap = 'KR'
            elif move.move_type == 'in_refund':
                # Note de credit fournisseur
                move_key_sap = 'KG'
        elif move.journal_id.type == 'bank':
            for line in move.line_ids:
                if line.account_id.user_type_id.type == 'receivable':
                    # paiement client
                    move_key_sap = 'DZ'
                    break
                elif line.account_id.user_type_id.type == 'payable':
                    # paiement fournisseur
                    move_key_sap = 'KZ'
                    break
        elif move.journal_id.type == 'general':
            move_key_sap = 'SA'
        return move_key_sap

    @api.model
    def get_tax_key_sap(self, move):
        "Return SAP codification"
        tax_ids = self.env['account.tax']
        for line in move.line_ids:
            tax_ids |= line.tax_ids

        if len(tax_ids) > 1:
            raise ValidationError(_("Too many taxes for account move (id: %d) trying to export") % move.id)
        elif len(tax_ids) == 1:
            sap_tax_code = tax_ids[0].export_code
            if not sap_tax_code:
                raise ValidationError(_("This taxes has no SAP code to export") % tax_ids[0].name)
        else:
            sap_tax_code = '/'

        return sap_tax_code

    @api.model
    def get_base_tax(self, move_line):
        "Return SAP codification"
        if move_line.tax_base_amount:
            res = "%s" % (move_line.tax_base_amount or '/')
        else:
            res = "/"
        return res

    @api.model
    def get_base_date(self, move_line):
        "Return SAP codification"
        if move_line.account_id.user_type_id.type in ['receivable'] and move_line.move_id.move_type == 'out_invoice':
            base_date = move_line.move_id.invoice_date or move_line.move_id.date
            res = base_date.strftime('%Y%m%d')
        else:
            res = "/"
        return res

    def export_move_and_move_line_sap(self):
        "main function"

        for wizard in self:
            data_of_file = ''.encode('ascii')

            condition = [
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('export_id', '=', False),
                ('state', 'not in', ['cancel', 'draft'])
            ]
            if wizard.journal_type != 'all':
                condition.add(('journal_id.type', '=', wizard.journal_type))
            move_ids = self.env['account.move'].search(condition)

            for move in move_ids:
                move_key_sap = self.get_move_key_sap(move)

                file_data = [
                    'ODOO',
                    str(move.id) or '/',
                    '/',
                    move.date.strftime('%Y%m%d') if move.date else '/',
                    txt_cleanup(move_key_sap or '/'),
                    move.company_id.code_company or '/',
                    move.date.strftime('%Y%m%d') if move.date else '/',
                    txt_cleanup(move.currency_id.name) or '/',
                    txt_cleanup(str(move.ref).split('-')[0] if '-' in str(move.ref) else move.ref if move.ref else '/'),
                    txt_cleanup(move.name or '/'),
                    '/',
                ]
                widths = (10, 10, 10, 8, 2, 4, 8, 5, 16, 25, 1)
                file_data = map(str, file_data)
                data_of_file += format_line(file_data, widths)

            # Attachment txt
            attachment_vals = {}
            attachment_vals['datas'] = base64.encodebytes(data_of_file)
            attachment_vals['mimetype'] = 'text/plain'
            attachment_vals['description'] = "Export comptable SAP"
            attachment_vals['name'] = "wizard_%s.txt" % (wizard.id)
            attachment_vals['res_model'] = 'account.export.sap.history'
            attachment = self.env['ir.attachment'].create(attachment_vals)

            file_name = 'export_compta_ENT_%s_%s_%s.txt' % (
                fields.Date.today(),
                wizard.journal_type,
                attachment.id)
            attachment.name = file_name
            wizard.attachment_id = attachment
            wizard.state = 'get'
            # History export
            history_vals = {'date': fields.Date.today()}
            history_vals['name_m'] = "du %s au %s: %s En-tête pieces %s" % (
                wizard.date_from, wizard.date_to,
                len(move_ids), wizard.journal_type)
            history_vals['name'] = "du %s au %s: %s pieces %s" % (
                wizard.date_from, wizard.date_to,
                len(move_ids), wizard.journal_type)
            history_vals['attachment_id'] = attachment.id
            history = self.env['account.export.sap.history'].create(history_vals)

            # Complete info
            attachment.res_id = history.id
            attachment.res_name = file_name
            move_ids.write({'export_id': history.id})
            wizard.message = history_vals['name']

            # Account move line
            data_of_ml_file = ''.encode('ascii')

            for move in move_ids:
                tax_key_sap = self.get_tax_key_sap(move=move)

                for line in move.line_ids:

                    base_vat = self.get_base_tax(line)
                    base_date = self.get_base_date(line)
                    code_account = self.get_account_sap(line)
                    account_key_sap = self.get_account_key_sap(line)

                    file_ml_data = [
                        str(line.move_id.id) or '/',
                        '/',
                        account_key_sap or '/',
                        code_account or '/',
                        txt_cleanup_price(locale.format('%.2f', line.credit) if line.credit else locale.format('%.2f', line.debit)) or '/',
                        '/',
                        txt_cleanup(tax_key_sap or '/'),
                        txt_cleanup(line.name or '/'),
                        txt_cleanup(line.analytic_account_id.code if line.analytic_account_id and line.journal_id.type == 'purchase' else '/'),
                        '/', '/',
                        '/',
                        '/',  # quantity
                        '/',  # date de valeur
                        '/', '/', '/', '/', '/', '/',
                        txt_cleanup(base_vat or '/'),
                        '/', '/',
                        txt_cleanup(base_date or '/'),
                        '/', '/', '/', '/', '/', '/', '/', '/', '/', '/', '/', '/',
                        txt_cleanup(line.analytic_account_id.code if line.analytic_account_id and line.journal_id.type == 'sale' else '/'),
                    ]

                    widths = (10, 10, 2, 17, 16, 16, 2, 50, 10, 12, 8, 17, 3, 8, 10, 4, 2, 4, 2, 3, 16, 16, 18, 8, 8, 1, 1, 1, 16, 16, 4, 3, 6, 3, 6, 3, 10)
                    file_ml_data = map(str, file_ml_data)
                    data_of_ml_file += format_line(file_ml_data, widths)

            move_lines_ids = move_ids.mapped('line_ids')
            # Attachment txt
            attachment_ml_vals = {}
            attachment_ml_vals['datas'] = base64.encodebytes(data_of_ml_file)
            attachment_ml_vals['mimetype'] = 'text/plain'
            attachment_ml_vals['description'] = "Export comptable SAP"
            attachment_ml_vals['name'] = "wizard_%s.txt" % (wizard.id)
            attachment_ml_vals['res_model'] = 'account.export.sap.history'
            attachment_ml = self.env['ir.attachment'].create(attachment_ml_vals)

            file_ml_name = 'export_compta_LIG_%s_%s_%s.txt' % (
                fields.Date.today(),
                wizard.journal_type,
                attachment_ml.id)
            attachment_ml.name = file_ml_name
            wizard.attachment_ml_id = attachment_ml
            # History export
            if history:
                history.update({'name_ml': "du %s au %s: %s postes de pieces %s" % (
                    wizard.date_from, wizard.date_to,
                    len(move_lines_ids), wizard.journal_type),
                    'attachment_ml_id': attachment_ml.id})

                # Complete info
                attachment_ml.res_id = history.id
                attachment_ml.res_name = history.name_ml
                move_lines_ids.write({'export_id': history.id})
                wizard.message_ml = history.name_ml

