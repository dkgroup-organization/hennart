# -*- coding: utf-8 -*-

# TODO: to rewrite, old project
CEGID_LINE_LENGTH = 232

CEGID_FORMAT_M = """type;1;1;M;Type
compte;2;8;;Numéro de compte
journal2;10;2;;Code journal sur 2 caractère
folio;12;3;000;folio
date;15;6;;Date écriture (JJMMAA)
code_libelle;21;1;;Code libellé 21 1
libelle_libre;22;20;;Libellé libre 22 20
sens;42;1;;Sens Débit/Crédit (D/C) 42 1
montant;43;13;;Montant en centimes signé (position 43=signe) 43 13
compte_contrepartie;56;8;;Compte de contrepartie 56 8
date_echeance;64;6;;Date échéance (JJMMAA) 64 6
lettrage;70;2;;Code lettrage 70 2
statistiques;72;3;;Code statistiques 72 3
piece5;75;5;;N° de pièce sur 5 caractères maximum 75 5
affaire;80;10;;Code affaire 80 10
quantite;90;10;;Quantité 1 90 10
piece8;100;8;;Numéro de pièce jusqu'à 8 caractères 100 8
devise;108;3;EUR;Code devise (FRF ou EUR, Espace = FRF, ou Devise) 108 3
journal3;111;3;;Code journal sur 3 caractères 111 3
code_tva_gestion;114;1;O;Flag Code TVA géré dans l'écriture = O (oui) 114 1
code_tva;115;1;;Code TVA 115 1
calcul_tva;116;1;D;Méthode de calcul TVA
Libelle;117;30;;Libellé écriture sur 30 caract. (blanc si renseigné en 22 sur 20
code_tva2;147;2;;Code TVA sur 2 caractères 147 2
piece10;149;10;;N° de pièce alphanumérique sur 10 caract. 149 10
Reserve;159;10;;Réservé
montant_devise;169;13;;seulement Montant dans la devise (en centimes signés position 169=signe) 
piece_jointe;182;12;;QC Windows Pièce jointe à l'écriture, nom du fichier sur 8 caractères + 169=signe) 
quantite2;194;10;;Quantité 2 194 10
numuniq;204;10;;NumUniq 204 10
operateur;214;4;;Code opérateur 214 4
date_sys;218;14;;Date système 218 14"""


@api.model
def get_cegid_format_m(self):
    """ read file with the definition of CEGID format
    return dictionnnary with : name of field: (start position int, width int, value text)
    The CSV file column are : code;position;width;default;description"""
    res = {}
    config = CEGID_FORMAT_M.split('\n')

    for raw in config:
        raw = raw.split(';')
        res[raw[0]] = {'start': int(raw[1]) - 1,
                       'width': int(raw[2]),
                       'end': int(raw[1]) - 1 + int(raw[2]),
                       'default': raw[3],
                       }
    return res


def button_export_line(self):
    "export the account move line"

    for wizard in self:
        def format_data_line(data_line, conf_line):
            """ return a CEGID formated line"""
            data_line_text = ' ' * format_cegid.CEGID_LINE_LENGTH
            for field_name in list(data_line.keys()):
                if len(data_line[field_name]) != conf_line[field_name]['width']:
                    raise ValidationError('The length of this value %s is not ok:\n>>>%s<<< ' % (
                        field_name, data_line[field_name]))
                start = conf_line[field_name]['start']
                end = conf_line[field_name]['end']
                data_line_text = data_line_text[0:start] + data_line[field_name] + data_line_text[end:]
            return data_line_text

        def format_libelle(line, length):
            """ format libelle """
            move_name = ' ' + txt_cleanup(line.move_id.name)
            partner_name = txt_cleanup(line.move_id.partner_id.name)

            for search_txt in ['-DKPRINTING', '-DKDIGITAL', '-DKFACTORY', '-DKINDUSTRIE']:
                if search_txt in move_name:
                    move_name = move_name.replace(search_txt, '')

            if len(move_name) > length:
                text = move_name[:length]
            else:
                partner_len_max = length - len(move_name)
                if len(partner_name) > partner_len_max:
                    partner_name = partner_name[:partner_len_max]

                text = partner_name + ' ' * (length - len(move_name) - len(partner_name)) + move_name
            return text

        # Check the partner configuration
        partner_ko_ids = self.env['res.partner']
        msg = "This partner are not correctly configured:\n"

        # List the move to export
        condition = [
            ('date', '>=', wizard.date_from),
            ('date', '<=', wizard.date_to),
            ('journal_id.type', '=', wizard.journal_type),
            ('company_id', '=', wizard.company_id.id),
            ('export_id', '=', False),
            ('state', 'not in', ['cancel', 'draft'])
        ]
        move_ids = self.env['account.move'].search(condition)
        datas = []
        conf_line = self.get_cegid_format_m()

        # Prepare attachment
        temp_dir = tempfile.TemporaryDirectory()

        # Start extract line
        for move in move_ids:

            default_data_line = {}

            # Check if invoice pdf
            if move.is_invoice(include_receipts=True):
                pdf = self.env.ref('account.account_invoices').sudo().render_qweb_pdf(move.ids)
                # The pdf name is limite to 8 character in CEGID, so this name is ok
                pdf_name = "F%07i" % move.id
                path_name = os.path.join(temp_dir.name, pdf_name + '.pdf')
                pdf_file = open(path_name, 'wb')
                pdf_file.write(pdf[0])
                pdf_file.close()
                default_data_line['piece8'] = pdf_name
                default_data_line['piece_jointe'] = pdf_name + '.pdf'

            for line in move.sudo().line_ids:

                data_line = default_data_line.copy()
                data_line['type'] = 'M'

                # compte tiers
                if line.compte_tiers and line.compte_tiers[0] == '?':
                    partner_ko_ids |= line.move_id.partner_id
                elif line.compte_tiers:
                    add_blanck = conf_line['compte']['width'] - len(line.compte_tiers)
                    if add_blanck < 0:
                        add_blanck = 0

                    data_line['compte'] = line.compte_tiers + ' ' * add_blanck
                else:
                    data_line['compte'] = line.compte_tiers or line.account_id.export_code

                if partner_ko_ids:
                    continue

                data_line['journal2'] = line.journal_id.export_code2
                data_line['journal3'] = line.journal_id.export_code3
                data_line['folio'] = '000'
                data_line['code_libelle'] = 'F'
                data_line['date'] = line.move_id.invoice_date.strftime("%d%m%y") \
                                    or line.move_id.date.strftime("%d%m%y")
                if line.debit > line.credit:
                    data_line['sens'] = 'D'
                    data_line['montant'] = format_amount(line.debit, conf_line['montant']['width'])
                else:
                    data_line['sens'] = 'C'
                    data_line['montant'] = format_amount(line.credit, conf_line['montant']['width'])

                data_line['Libelle'] = format_libelle(line, conf_line['Libelle']['width'])
                data_line['piece10'] = "%010i" % line.move_id.id

                if line.date_maturity:
                    data_line['date_echeance'] = line.date_maturity.strftime("%d%m%y")

                datas.append(format_data_line(data_line, conf_line))

        if partner_ko_ids:
            for partner_ko in partner_ko_ids:
                msg += "%s\n" % partner_ko.name
            raise ValidationError(msg)

        # extract data
        content = ''
        for line in datas:
            content += line + '\n'

        wizard.content = content or ''

        # Create ZIP file with pdf
        file_name_txt = 'export_%s_%s.txt' % (fields.Date.today(), wizard.journal_type)
        path_name = os.path.join(temp_dir.name, file_name_txt)
        file_txt = open(path_name, 'w')
        file_txt.write(wizard.content)
        file_txt.close()

        # write files and folders to a zipfile
        zip_filename = tempfile.gettempdir() + '/export_%s_%s.zip' % (
        wizard.id, fields.Datetime.now().strftime('%Y%m%d_%H%M%S'))
        zip_file = zipfile.ZipFile(zip_filename, 'w')
        with zip_file:
            # write each file seperately
            for root, dirs, files in os.walk(temp_dir.name):
                for file in files:
                    zip_file.write(os.path.join(root, file), file)
        zip_file.close()

        # Attachment csv
        attachment_vals = {}
        zip_file = open(zip_filename, 'rb')
        attachment_vals['name'] = zip_filename
        attachment_vals['datas'] = base64.encodebytes(zip_file.read())
        zip_file.close()

        attachment_vals['mimetype'] = "application/zip"
        attachment_vals['description'] = "Export comptable CEGID"
        attachment_vals['res_model'] = 'account.export.history'
        attachment = self.env['ir.attachment'].create(attachment_vals)

        # change temporary name
        attachment.name = 'export_%s_%s_%s.zip' % (
            fields.Date.today(),
            wizard.journal_type,
            attachment.id)
        wizard.attachment_id = attachment

        # History export
        history_vals = {'date': fields.Date.today()}
        history_vals['name'] = "du %s au %s: %s pieces %s" % (
            wizard.date_from, wizard.date_to,
            len(move_ids), wizard.journal_type)
        history_vals['attachment_id'] = attachment.id
        history_vals['company_id'] = wizard.company_id.id

        history = self.env['account.export.history'].create(history_vals)

        # Complete info
        attachment.res_id = history.id
        move_ids.write({'export_id': history.id})
        wizard.message = history_vals['name']
