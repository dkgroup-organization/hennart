# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import os
import logging
import unicodedata
import tempfile
import time
import csv
#from . import format_cegid
#import zipfile

_logger = logging.getLogger(__name__)


def remove_accents(input_str):
    only_ascii = unicodedata.normalize('NFD', input_str).encode('ascii', 'ignore')
    if type(only_ascii) == bytes:
        return only_ascii.decode()
    else:
        return only_ascii


def txt_cleanup(text):
    if text:
        text = remove_accents(text)
        for checkchar in ['\"', '\r\n', '\n', ';', '%', '"', '   ', '  ', '  ']:
            text = text.replace(checkchar, ' ')
        text = text.strip()
        return text
    else:
        return ''


def format_amount(amount, length):
    """ return text with no point with a fixed lenght """
    c1 = ("%0.2f" % amount).replace('.', '')
    if len(c1) <= length:
        c2 = ' ' * (length - len(c1)) + c1
    else:
        # there is a problem
        msg = "This amount is to big: %0.2f\n%s" % (amount, length)
        raise ValidationError(msg)
    return c2


class AccountExportMoveLine(models.TransientModel):
    _name = 'account.export.moveline'
    _description = 'Export move line.'

    journal_type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('general', 'Divers')], string="Journal type", required=True)

    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    message = fields.Html('Message', readonly=True)
    content = fields.Text('Content')

    attachment_id = fields.Many2one('ir.attachment', string='File', readonly=True)
    attachment_name = fields.Char(related='attachment_id.name', readonly=True)
    attachment_datas = fields.Binary(related='attachment_id.datas', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def default_get(self, fields):
        "return default value"
        res = super(AccountExportMoveLine, self).default_get(fields)
        res['company_id'] = self.env.company.id
        return res

    @api.onchange('journal_type')
    def onchange_journal(self):
        "check last date change"
        if self.journal_type:

            condition = [
                ('journal_id.type', '=', self.journal_type),
                ('export_id', '=', False),
                ('date', '>=', '2022-01-01'),
                ('company_id', '=', self.company_id.id),
                ('state', 'not in', ['cancel', 'draft'])
            ]
            move_ids = self.env['account.move'].search(condition, order="date")
            if move_ids:
                self.date_from = move_ids[0].date
                self.date_to = move_ids[-1].date
                self.message = ''
            else:
                self.date_from = False
                self.date_to = False
                self.message = ''
        else:
            self.date_from = False
            self.date_to = False
            self.message = ''

    def button_export_line(self):
        "export the account move line"

        for wizard in self:

            condition = [
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('journal_id.type', '=', wizard.journal_type),
                ('company_id', '=', wizard.company_id.id),
                ('export_id', '=', False),
                ('state', 'not in', ['cancel', 'draft'])
                ]
            move_ids = self.env['account.move'].search(condition)

            column_template = ["account", "third", "debit", "credit", "amount_currency", "journal", "currency_rate",
                               "invoice", "date", "date_maturity", "libelle", "currency"]

            datas = []

            move_ids.check_tiers_account()
            #move_ids.check_account()

            # Start extract line
            for move in move_ids:
                for line in move.line_ids:

                    if not line.account_id:
                        continue

                    data_line = {}
                    data_line['account'] = line.account_id.export_code or line.account_id.code or ''
                    data_line['third'] = line.compte_tiers or ''
                    data_line['debit'] = line.debit
                    data_line['credit'] = line.credit
                    data_line['amount_currency'] = abs(line.amount_currency)
                    data_line['journal'] = line.journal_id.export_code or line.journal_id.code or ''
                    data_line['currency_rate'] = line.currency_rate
                    data_line['invoice'] = move.name or ''
                    data_line['date'] = move.invoice_date or move.date
                    data_line["date_maturity"] = line.date_maturity
                    data_line['libelle'] = move.partner_id.name or ''
                    data_line['currency'] = line.currency_id.name

                    # Unicode,currency_rate
                    for key in ['libelle']:
                        data_line[key] = txt_cleanup(data_line[key])



                    # Date format
                    for key in ['date', "date_maturity"]:
                        if data_line[key]:
                            date_txt = data_line.get(key).strftime('%d%m%Y')
                            data_line[key] = date_txt
                        else:
                            data_line[key] = ''

                    datas.append(data_line)

            content = ''
            for column in column_template:
                if content:
                    content += ';'
                content += column
            content += '\n'

            for data_line in datas:
                line_text = ''
                for column in column_template:
                    if column != column_template[0]:
                        line_text += ';'
                    if column in list(data_line.keys()):
                        line_text += "%s" % (data_line[column])
                content += line_text + '\n'

            wizard.content = content or ''

            # Attachment csv
            attachment_vals = {}
            attachment_vals['datas'] = base64.encodebytes(wizard.content.encode('utf-8'))
            attachment_vals['mimetype'] = "text/csv"
            attachment_vals['description'] = "Export comptable SAGE"
            attachment_vals['name'] = "wizard_%s.csv" % (wizard.id)
            attachment_vals['res_model'] = 'account.export.history'
            attachment = self.env['ir.attachment'].create(attachment_vals)

            file_name = 'export_%s_%s_%s.csv' % (
                            fields.Date.today(),
                            wizard.journal_type,
                            attachment.id)
            attachment.name = file_name
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
