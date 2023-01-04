# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging
log = logging.getLogger(__name__).info

from odoo.exceptions import UserError
import io
from io import StringIO
import base64

from datetime import datetime


class AccountMoveImport(models.TransientModel):
    _name = 'account.move.import'

    def controllers_load_header(self):
        assert (self.file and self.file_line), UserError(_('You must specify a file line to import and an file'))

        split_filename = self.filename.split('_')[-1].split('.a')[0]
        split_filename_line = self.filename_line.split('_')[-1].split('.a')[0]
        
        assert (split_filename == split_filename_line), UserError(_('You need insert same file and file line'))
        assert (self.filename != self.filename_line), UserError(_('You need insert different file'))

        account_move_data = self.convert_binary(self.file)
        self.get_line_to_import(account_move_data)

        return self.env['script.tools'].open_wizard(self)

    def controllers_import(self):
        assert (self.file and self.file_line), UserError(_('You must specify a file line to import and an file'))

        account_move_data = self.convert_binary(self.file)

        tmp = []
        for line, account_move in zip(self.line_ids, account_move_data):
            if str(line.id_account_move) == account_move[1] and line.selected:
                tmp.append(account_move)

        account_move_data = tmp
        account_move_line_data = self.convert_binary(self.file_line)
        data = self.regroup_data(account_move_data, account_move_line_data)

        if self.state == 'selection':
            self.create_in_odoo(data)
            return True

        return self.env['script.tools'].open_wizard(self)

    def convert_binary(self, binary):
        list_content = []
        content = base64.b64decode(binary).decode('iso-8859-1')
        content_value = content.replace(' ', '')
        content_data = content_value.split('\r\n')

        for line in content_data:
            value_listed = line.replace(';/', ';').split(';')
            list_content.append(value_listed)
        list_content = list_content[:-1]
        return list_content

    def regroup_data(self, account_move_data, account_move_line_data):
        list_move = []
        for value in account_move_data:
            dico = {
                'name': value[0],
                'id': value[1],
                '?': value[2],
                'date': value[3],
                'SC ?': value[4],
                'company': value[5],
                'date2': value[6],
                'devise': value[7],
                'wtf ?': value[8],
                'wtf 2 ?': value[9],
                'value possible ?': value[10],
                'line': []
            }
            list_move.append(dico)
        for dico in list_move:
            for line_value in account_move_line_data:
                if dico['id'] == line_value[0]:
                    dico_line = {
                        'id' : line_value[0],
                        '?': line_value[1],
                        'credit/debit' : line_value[2],
                        'account_id' : line_value[3],
                        'montant' : line_value[4],
                        '?2' : line_value[5],
                        '?3' : line_value[6],
                        'partner_id' : line_value[7],
                        'analytic_account_id' :  line_value[8],
                        '?5' : line_value[9],
                        'value_jsp' :  line_value[10],
                        '?6' : line_value[11],
                        '?7' :  line_value[12],
                        '?8' : line_value[13],
                        '?9' :  line_value[14],
                    }
                    dico['line'].append(dico_line)
        return list_move

    def create_in_odoo(self, data):
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        ResCompany = self.env['res.company']
        ResCurrency = self.env['res.currency']
        AccountAccount = self.env['account.account']
        AccountAnalytic = self.env['account.analytic.account']

        for account_move in data:
            company_id = ResCompany.search([('name', '=', account_move['company'])])
            date = datetime.strptime(account_move['date'], '%Y%m%d')
            date2 = datetime.strptime(account_move['date2'], '%Y%m%d')
            devise = ResCurrency.search([('name', '=', account_move['devise'])])
            lines = AccountMoveLine
            name = account_move['company'] + '_' + self.filename.split('_')[-1].split('.a')[0] + '_' + account_move['id']
            account_created = AccountMove.create({
                'name': name,
                'currency_id' : devise.id,
                'date' : date
            })

            for value_line in account_move['line']:
                account_id = AccountAccount.search([
                    ('code', '=', value_line['account_id'])
                ])

                assert account_id, UserError(_('An error occurred while creating the account line because the journal was was not created : %s', value_line['account_id'] + ' ' + value_line['partner_id']))

                dico_create = {
                    'account_id' : account_id.id,
                    'move_id' : account_created.id
                }

                analytic_account_id = AccountAnalytic
                if value_line['analytic_account_id']:
                    analytic_account_id = AccountAnalytic.search([
                        ('name', '=',  value_line['analytic_account_id'])
                    ])
                    if not analytic_account_id:
                        analytic_account_id = AccountAnalytic.create({
                            'name' : value_line['analytic_account_id'],
                            'currency_id' : devise.id
                        })
                    dico_create['analytic_account_id'] = analytic_account_id.id

                if value_line['credit/debit'] == '50':
                    dico_create['credit'] = float(value_line['montant'])
                elif value_line['credit/debit'] == '40':
                    dico_create['debit'] = float(value_line['montant'])

                lines |= AccountMoveLine.with_context(check_move_validity=False).create(dico_create)

    def get_line_to_import(self, data):
        for account_move in data:
            self.line_ids.create({
                    'name_company' : account_move[5],
                    'line_id' : self.id,
                    'id_account_move' : account_move[1] # permet d'eviter les duplicata si une societe est presente plusieurs fosi dans le fichier
                })
        self.state = 'selection'

    state = fields.Selection([
             ('draft', _('Draft')),
             ('selection', _('Selectionned')),
             ('imported', _('Imported')),
        ], string=_('State'), default='draft')

    file_line = fields.Binary()
    filename_line = fields.Char()
    file = fields.Binary()
    filename = fields.Char()
    line_ids = fields.One2many('account.move.import.line', 'line_id', string=_('line to import'))
