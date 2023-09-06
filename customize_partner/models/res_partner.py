# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cadence = fields.Html(string="Cadencier", compute="compute_cadence")
    is_customer = fields.Boolean('Customer')
    is_supplier = fields.Boolean('Supplier')

    @api.model_create_multi
    def create(self, vals_list):
        search_partner_mode = self.env.context.get('res_partner_search_mode')
        is_customer = search_partner_mode == 'customer'
        is_supplier = search_partner_mode == 'supplier'
        if search_partner_mode:
            for vals in vals_list:
                if is_customer:
                    vals['is_customer'] = True
                elif is_supplier:
                    vals['is_supplier'] = True
        return super().create(vals_list)

    @api.onchange('is_customer', 'is_supplier')
    def change_rank(self):
        """ Check minimum rank"""
        for partner in self:
            if partner.is_customer and partner.customer_rank <= 0:
                partner.customer_rank = 1
            elif not partner.is_customer:
                partner.customer_rank = 0

            if partner.is_supplier and partner.supplier_rank <= 0:
                partner.supplier_rank = 1
            elif not partner.is_supplier:
                partner.supplier_rank = 0

    def compute_cadence(self):
        # cadencier
        # Create the name of the column
        for rec in self:
            # If there is data for the product, create a table to display the quantity sold by week
            cadence_table = '<div id="cadence" class="col-10 ms-auto me-auto"> <table class="table table-bordered"><thead class="table-light"><tr><th style="font-weight: bold; text-align: center;border-left: 1px solid grey; width:30%;"> Produit </th>'
            style_td = 'border-left: 1px solid grey; width:4%;'
            style_text = ' font-weight: bold; text-align: center;'
            date_start = datetime.now()
            date_start = date_start - timedelta(days=date_start.weekday())
            date_from = datetime.now() - timedelta(weeks=13)
            for week in range(0, 13):
                cadence_table += '<th style="%s">%s</th>' %(style_td + style_text, str(-week))
            cadence_table +='</tr></thead><tbody>'
            condition = [
                ('move_id.partner_id', '=', rec.id),
                ('move_id.invoice_date', '<', date_start),
                ('move_id.invoice_date', '>=', date_from),
                ('move_id.state', '!=', 'cancel'),
                ('move_id.move_type', '=', 'out_invoice'),
            ]
            invoice_lines = self.env['account.move.line'].search(condition)
            for product_id in invoice_lines.mapped('product_id'):
                cadence_table += '<tr><td>[%s] %s </td>' %(product_id.default_code, product_id.name)
                pack = product_id.base_unit_count if product_id.base_unit_count> 0.0 else 1
                for week in range(0, 13):
                    date_to = date_start - timedelta(weeks=week - 1)
                    date_from = date_start - timedelta(weeks=week)
                    qty = sum(invoice_lines.filtered(lambda
                                                     l: l.product_id.id == product_id.id
                                                        and date_from.date() <= l.move_id.invoice_date <= date_to.date()).mapped('uom_qty'))
                    qty_text = int(qty / pack) if qty > 0.0 else ""
                    cadence_table += '<td> %s </td>' %(qty_text)
                cadence_table +='</tr>'
            cadence_table += '</tbody></table></div>'
            rec.cadence = cadence_table

    def get_function(self):
        """ Save function"""
        for partner in self:
            function_txt = ""
            for function in partner.email_function:
                function_txt += " %s" % function.name
            partner.function = function_txt

    @api.depends('child_ids.email_function')
    def get_function_email(self):
        """ return email by function"""
        for partner in self:
            if partner.is_company:
                parent = partner
            elif partner.parent_id:
                parent = partner.parent_id
            else:
                parent = partner

            default_email = parent.email
            contact_function = {}
            for contact in parent.child_ids:
                if not contact.email:
                    continue
                for function in contact.email_function:
                    if function.code not in list(contact_function.keys()):
                        contact_function[function.code] = contact.email
                    else:
                        contact_function[function.code] += ',' + contact.email

            for code in ['email_delivery', 'email_accounting', 'email_director', 'email_vendor', 'email_sale',
                         'email_quality', 'email_department_manager', 'email_other']:
                setattr(partner, code, contact_function.get(code) or default_email)

    def put_function_email(self):
        """ check and create a contact for new email"""
        for partner in self:
            if not partner.is_company:
                continue
            dic_function = {
                'email_delivery': partner.email_delivery,
                'email_accounting': partner.email_accounting,
                'email_director': partner.email_director,
                'email_vendor': partner.email_vendor,
                'email_sale': partner.email_sale,
                'email_quality': partner.email_quality,
                'email_department_manager': partner.email_department_manager,
                'email_other': partner.email_other,
                }
            dic_email = {}

            for code, list_email in dic_function.items():
                if not list_email:
                    continue

                # format list_email with comas separator
                list_email = list_email.lower().strip().replace(' ', ',').replace(';', ',').replace(',,,', ',').replace(',,', ',').replace(',,', ',')
                dic_function[code] = list_email

                for email in list_email.split(','):
                    if not email in list(dic_email.keys()):
                        dic_email[email] = []
                    if not code in dic_email[email]:
                        dic_email[email].append(code)

            for email in list(dic_email.keys()):
                if not email:
                    continue

                condition = [('parent_id', '=', partner.id), ('email', '=', email)]
                contact_ids = self.search(condition)
                if not contact_ids and email == partner.email:
                    continue

                if not contact_ids:
                    contact_ids = contact_ids.create({
                        'parent_id': partner.id,
                        'name': email,
                        'email': email,
                    })
                function_ids = self.env['res.partner.function'].search([('code', 'in', dic_email[email])])
                contact_vals = {'email_function': [(6, 0, function_ids.ids)]}
                contact_ids.write(contact_vals)
            partner.update(dic_function)

    @api.onchange('name')
    def onchange_name(self):
        """ Only ASCII and upper char """
        only_ascii = unicodedata.normalize('NFD', self.name or '').encode('ascii', 'ignore')
        self.name = only_ascii.upper()

    # Sale data
    sale_area = fields.Many2one('res.partner.area', string="Sale area")
    discount_weight = fields.Float('Discount weight (kg)')
    typology_id = fields.Many2one('res.partner.typology', string='Typology')


    # email data
    v7_function = fields.Char('V7 save function value')
    function = fields.Char('Function', compute="get_function")
    email_delivery = fields.Char('Email delivery', compute='get_function_email', inverse="put_function_email", store=True)
    email_accounting = fields.Char('Email accounting', compute='get_function_email', inverse="put_function_email", store=True)
    email_director = fields.Char('Email director', compute='get_function_email', inverse="put_function_email", store=True)
    email_vendor = fields.Char('Email vendor', compute='get_function_email', inverse="put_function_email", store=True)
    email_sale = fields.Char('Email Sale', compute='get_function_email', inverse="put_function_email", store=True)
    email_quality = fields.Char('Email quality', compute='get_function_email', inverse="put_function_email", store=True)
    email_department_manager = fields.Char('Email department manager', compute='get_function_email', inverse="put_function_email", store=True)
    email_other = fields.Char('Email other', compute='get_function_email', inverse="put_function_email", store=True)
    email_function = fields.Many2many('res.partner.function', string="Functions")

    # preparation data
    print_picking = fields.Boolean('Print Delivery', default=True, help="Print Delivery at the end of preparation")
    print_picking2 = fields.Boolean('Print Delivery with price', default=True, help="Print Delivery with price at the end of preparation")

    print_invoice = fields.Boolean('Print Invoice', default=True, help="Print Invoice at the end of preparation")
    paper_invoice = fields.Boolean('Paper invoice by mail', default=False, help="Send paper invoice by physical mail")
    email_invoice = fields.Boolean('Automatic email pdf invoice', default=False)
    invoice_auto = fields.Boolean('Automatic validation', default=True,
            help="The invoice is automatically validated at the end of preparation")
    no_invoice_auto = fields.Boolean('Manual Invoice', default=False,
            help="The invoice is not automaticaly created, so it's possible to group the delivery in one invoice or don't invoice some partner")

    # Carrier and export
    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm',
                                  help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    incoterm_contact_id = fields.Many2one('res.partner', string="Incoterm contact")
    incoterm_city = fields.Char("Incoterm City")
    carrier_zone = fields.Char("Carrier zone")
    oeri_code = fields.Char("OERI code")
    label_forced = fields.Boolean('label all packages', default=False)
    label_all_product = fields.Boolean('label all products', default=False)
    label_needed = fields.Boolean('label according to product sheet', default=False)
    hour_delivery = fields.Float('Hour delivery', default=0.0)
    payment_method_id = fields.Many2one("account.payment.method", string="Payment method")




    def button_update_partner(self):
        "Update partner after import"
        pass
