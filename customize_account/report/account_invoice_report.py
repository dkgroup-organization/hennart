from odoo import models, fields, tools, api

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    cost_price = fields.Float(string="Cost Price", readonly=True)
    margin = fields.Float(string='Marge', readonly=True)
    promo = fields.Float(string='Promo', readonly=True)
    weight = fields.Float(string="Weight", readonly=True)
    user2_id = fields.Many2one('res.users', string="Vendeur Manager", readonly=True)
    partner_shipping_id = fields.Many2one('res.partner', string="Partner Livraison", readonly=True)
    team_id = fields.Many2one(comodel_name='crm.team', string="Sales Team")
    uom_qty = fields.Float(string="Quantity unit", readonly=True)
    week = fields.Integer(string="Semaine", readonly=True)
    month = fields.Integer(string="Mois", readonly=True)

    @api.model
    def _select(self):

        """ (line.margin * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)) AS margin,"""
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.journal_id,
                line.company_id,
                partner.user2_id,
                (line.cost_price * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)) AS cost_price,
                line.cadeau AS promo,
                (CASE
                    WHEN template.name ILIKE '- Remise%' THEN 0.0
                    ELSE (line.margin * 
                        (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                    )
                END) AS margin,
                (line.weight * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)) AS weight,
                line.partner_shipping_id,
                line.company_currency_id,
                line.partner_id AS commercial_partner_id,
                account.account_type AS user_type,
                move.state,
                move.team_id as team_id,
                move.move_type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.payment_state,
                move.invoice_date,
                EXTRACT(WEEK FROM move.invoice_date) as week,
                EXTRACT(MONTH FROM move.invoice_date) as month,
                move.invoice_date_due,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                line.uom_qty * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS uom_qty,                                                     
                -line.balance * currency_table.rate                         AS price_subtotal,
                line.price_total * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS price_total,
                COALESCE(
                   -- Average line price
                   (line.balance / NULLIF(line.quantity, 0.0)) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                   -- convert to template uom
                   * (NULLIF(COALESCE(uom_line.factor, 1), 0.0) / NULLIF(COALESCE(uom_template.factor, 1), 0.0)),
                   0.0) * currency_table.rate                               AS price_average,
                COALESCE(shipping_partner.country_id, partner.country_id, commercial_partner.country_id) AS country_id,
                line.currency_id                                            AS currency_id
        '''

    @api.model
    def _from(self):
        sql_from =  '''
            FROM account_move_line line
                LEFT JOIN res_partner partner ON partner.id = line.partner_id
                LEFT JOIN product_product product ON product.id = line.product_id
                LEFT JOIN account_account account ON account.id = line.account_id
                LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
                LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
                INNER JOIN account_move move ON move.id = line.move_id
                LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id
                LEFT JOIN res_partner shipping_partner ON shipping_partner.id = move.partner_shipping_id
                JOIN {currency_table} ON currency_table.company_id = line.company_id
        '''.format(
            currency_table=self.env['res.currency']._get_query_currency_table({'multi_company': True, 'date': {'date_to': fields.Date.today()}}),
        )
        return sql_from

    @api.model
    def _where(self):
        return '''
            WHERE move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                AND line.account_id IS NOT NULL
                AND line.display_type = 'product'
        '''