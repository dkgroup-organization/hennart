# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductArea(models.Model):
    _name = 'product.area'
    _description = "Geographical area"
    name = fields.Char(string='Name', required=True, translate=True)


class ProductAllergen(models.Model):
    _name = 'product.allergen'
    _description = "Allergenic component "
    name = fields.Char(string='Name', required=True, translate=True)


class ProductIngredient(models.Model):
    _name = 'product.ingredient'
    _description = "Ingredient"
    name = fields.Char(string='Name', required=True, translate=True)


class ProductSpecificity(models.Model):
    _name = 'product.specificity'
    _description = "Spécificity"
    name = fields.Char(string='Name', required=True, translate=True)
    
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @tools.ormcache()
    def _get_default_uos_id(self):
        return self.env.ref('uom.product_uom_unit')

    service_type = fields.Selection(
        [('manual', 'Manually set quantities on order')], string='Track Service',
        compute='_compute_service_type', store=True, readonly=False, precompute=False, default="manual",
        help="Manually set quantities on order: Invoice based on the manually entered quantity, without creating an analytic account.\n"
             "Timesheets on contract: Invoice based on the tracked hours on the related timesheet.\n"
             "Create a task and track hours: Create a task on the sales order validation and track the work hours.")

    invoice_policy = fields.Selection(
        [('order', 'Ordered quantities'),
         ('delivery', 'Delivered quantities')], string='Invoicing Policy',
        compute='_compute_invoice_policy', store=True, readonly=True, precompute=False, default="delivery",
        help='Ordered Quantity: Invoice quantities ordered by the customer.\n'
             'Delivered Quantity: Invoice quantities delivered to the customer.')

    route_ids = fields.Many2many(default=False)
    uos_id = fields.Many2one('uom.uom', string='Unit of Sale',
                             default=_get_default_uos_id, required=True,
                             help="Default unit of Sale used for invoicing.")
    code_ean_prix = fields.Char('Code EAN Prix', size=12)
    code_ean_poids = fields.Char('Code EAN Poids', size=12)
    code_DUN14 = fields.Char('Code DUN14', size=14)
    not_solded = fields.Boolean(string='No longer sold')
    region = fields.Char('Region')
    department = fields.Char('Department')

    area = fields.Many2one(string='Area', comodel_name='product.area')
    ingredient = fields.Many2many('product.ingredient', 'ingredient_rel', string="Ingredient")
    allergen = fields.Many2many('product.allergen', 'allereg_reel', string="Allergen")
    production_specificity = fields.Many2many('product.specificity','specifit_reel', string="Production specifity",
                                              help='define some spécificity like OGM, IGP, farmer, presence of GMO')
    specificity_milk = fields.Selection(
        selection=[
            ('farmer', 'Farmer'),
            ('craft', 'Craft'),
            ('cooked_pressed', 'Cooked pressed dough'),
            ('uncooked_pressed', 'Uncooked pressed dough'),
            ('veined', 'Veined cheese dough'),
            ('natural_rind', 'Natural rind soft cheese'),
            ('washed_rind', 'Soft washed rind'),
            ('fuzzy_rind', 'Soft fuzzy rind'),
            ('processed', 'Processed product'),
            ('fees', 'Fees and Butter'),
            ('tray', 'Tray'),
            ('craft', 'Craft'),
            ('other', 'Other'),
        ],
        string='Technical family')
    heat_treatment_milk = fields.Selection(
        selection=[
            ('raw', 'Raw'),
            ('thermised', 'Thermised'),
            ('pasteurized', 'Pasteurized'),
            ('other', 'Other'),
        ],
        string='Heat treatment of milk')

    rennet = fields.Selection(
        selection=[
            ('animal', 'Animal'),
            ('fermentative', 'Fermentative'),
            ('microbial', 'Microbial'),
            ('other', 'Other'),
        ],
        string='Rennet')

    salting = fields.Selection(
        selection=[
            ('dry', 'Dry'),
            ('brine', 'Brine'),
        ],
        string='Salting')

    pate_molle = fields.Boolean(string='Pate molle')
    type_milk = fields.Selection(
        selection=[
            ('cow', 'Cow'),
            ('goat', 'Goat'),
            ('sheep', 'Sheep'),
            ('vegetable', 'Vegetable'),
            ('other', 'Other'),
        ],
        string='Type milk')

    nv_energy_kj = fields.Char(string=' Energy (Kj)')
    nv_energy_kc = fields.Char(string=' Energy (Kcal)')
    nv_fat = fields.Char(string='FAT (g)')
    fat_in_dry_matter = fields.Char(string='Fat in dry matter (%)')
    nv_saturated_fatty_acids = fields.Char(string='Saturated fatty acids (g)')
    nv_carbohydrates = fields.Char(string='Carbohydrates (g)')
    nv_sugars = fields.Char(string='Sugars (g)')
    nv_protein = fields.Char(string=' Protein (g)')
    nv_salt = fields.Char(string='Salt (g)')

    life_date = fields.Boolean(string='DLC : Expiration Date')
    use_date = fields.Boolean(string='DDM : Best before Date')

    tare = fields.Float(string='Tare', digits="Stock Weight",
        help='Tare, this value will be subtracted from the weight returned by the device to obtain the net weight. ')
    weight_gross = fields.Float(string='Gross Weight', help='The gross weight in Kg.', digits="Stock Weight")
    format_etiquette = fields.Char('Format d\'etiquette', size=128)

    # Production
    gestion_affinage = fields.Boolean(string='Maturing management', compute='compute_gestion_affinage', store=False)
    min_production_qty = fields.Float(string='Batch production quantity',
                                help = "The production is manufactured in multiples of this number.")
    to_personnalize = fields.Boolean(string='Customer specifity',
                                     help="This product need a production opération to be personnalized."
                                          " For exemple, label with brand."
                                          "This product cannot be sold to another customer")
    to_label = fields.Boolean(string='To label',
                                     help="This product need a wheighted opération")

    # LABEL
    aop = fields.Boolean(string='AOP')
    ogm = fields.Boolean(string='OGM')
    igp = fields.Boolean(string='IGP')
    farmer_type = fields.Boolean(string='Type Fermier')

    approval_number = fields.Char(string='N° Agrément')

    # WEB description
    web_historic = fields.Html('Historic')
    web_manufacture = fields.Html('Manufacture')
    web_tasting = fields.Html('Tasting')

    base_unit_count = fields.Float('Unit Count', compute="compute_package", store=True, default=1.0,
        help="Number of unit in the package.")

    base_unit_price = fields.Float("Price Per Unit", compute="compute_package", store=True, default=0.0,
        help="Price of unit in the package.")

    base_package_price = fields.Float("Price total", compute="compute_package", store=True, default=0.0,
        help="Price of the package.")

    base_product_tmpl_id = fields.Many2one("product.template", string="Unit product",
                                        compute="compute_package", store=True)

    base_unit_name = fields.Char(compute='_compute_base_unit_name',
                                 help='Displays the custom unit for the products if defined or the selected unit of measure otherwise.')

    average_cost_price = fields.Float(
        string="Average Purchase (6 month)",
        help="Average purchase price based on last 6 months vendor's invoices",
        compute="compute_average_cost_price",
        store=True
    )

    current_cost_price = fields.Float(
        string="Current Purchase",
        help="Average purchase price of stock.",
        compute="compute_current_cost_price",
    )

    refinement_cost = fields.Float(
        string="Refinement Cost (€)",
        help="Refinement cost in € for the products"
    )

    cutting_cost = fields.Float(
        string="Cutting Cost (€)",
        help="Cost of transforming the product in €"
    )

    transformation_cost = fields.Float(
        string="Transformation Cost (€)",
        help="Cost of cutting and packaging the product in €"
    )

    total_cost_price = fields.Float(
        string="Total Cost Price",
        help="Average Purchase Price + Refinement, Cutting and Transformation Costs"
    )

    workshop_cost_price = fields.Float(
        'Workshop Cost Price', compute='_compute_standard_price',
        digits='Product Price', groups="base.group_user",
        help="""Used to value the product and margins on sale orders. Based on total cost price.""")

    standard_price = fields.Float(
        'Workshop Cost Price', compute='_compute_standard_price',
        inverse='_set_standard_price', search=False,
        digits='Product Price', groups="base.group_user",
        help="""Used to value the product cost by unit based on total cost price.""")

    component_price = fields.One2many('product.component.hierarchy', 'product_tmpl_id', string='Component')


    def get_coef_workshop_cost(self):
        """ return coef to apply between workshop_cost_price and total_cost_price """
        return 1.12

    @api.depends('total_cost_price', 'weight', 'uos_id')
    def _compute_standard_price(self):
        """ Compute the standard price """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for product in self:
            coef_workshop_cost = product.get_coef_workshop_cost()
            product.workshop_cost_price = product.total_cost_price * coef_workshop_cost

            if product.uos_id == uom_weight and product.weight:
                standard_price = product.workshop_cost_price * product.weight
            elif product.uos_id == uom_weight and not product.weight:
                standard_price = 0.0
            else:
                standard_price = product.workshop_cost_price

            product.standard_price = standard_price

    def compute_average_cost_price(self):
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for product in self:
            # Définir la date de début des 6 derniers mois
            date_six_months_ago = fields.Date.to_date(fields.Date.context_today(self)) - timedelta(days=180)

            if product.base_unit_count > 1:
                base_product_ids = product.base_product_tmpl_id.product_variant_ids.ids
            else:
                base_product_ids = product.product_variant_ids.ids

            # Récupérer les lignes de facture d'achat pour ce produit des 6 derniers mois
            invoice_lines = self.env['account.move.line'].search([
                ('product_id', 'in', base_product_ids),
                ('move_id.move_type', '=', 'in_invoice'),  # Filtre les factures d'achat
                ('move_id.state', '=', 'posted'),  # Seulement les factures validées
                ('move_id.invoice_date', '>=', date_six_months_ago)
            ])
            # Calcul du prix moyen pondéré
            total_cost_quantity = 0.0
            total_cost_weight = 0.0
            total_quantity = 0.0
            total_weight = 0.0

            for line in invoice_lines:
                if line.product_uom_id == uom_weight:
                    total_weight += line.quantity
                    total_cost_weight += line.price_subtotal
                else:
                    total_quantity += line.quantity
                    total_cost_quantity += line.price_subtotal

            if total_weight:
                product.average_cost_price = total_cost_weight / total_weight
            elif total_quantity:
                product.average_cost_price = total_cost_quantity / total_quantity
            else:
                product.average_cost_price = 0.0

    def compute_current_cost_price(self):
        """ compute current stock value """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for product in self:
            # Product in stock
            if product.base_unit_count > 1:
                base_product_ids = product.base_product_tmpl_id.product_variant_ids.ids
            else:
                base_product_ids = product.product_variant_ids.ids

            # Récupérer les lignes de stock avec leur valeur
            quant_ids = self.env['stock.quant'].search([
                ('product_id', 'in', base_product_ids),
                ('location_id.usage', '=', 'internal'),
                ('lot_id', '!=', False)
                ])

            # Récupérer les lignes de facture d'achat pour ce produit des 6 derniers mois
            invoice_line_lot = self.env['account.move.line.lot'].search([
                ('product_id', 'in', base_product_ids),
                ('account_move_line_id.move_id.move_type', '=', 'in_invoice'),  # Filtre les factures d'achat
                ('account_move_line_id.move_id.state', '=', 'posted'),  # Seulement les factures validées
                ('lot_id', 'in', quant_ids.lot_id.ids)
                ])

            # Calcul du prix moyen pondéré
            total_cost_quantity = 0.0
            total_cost_weight = 0.0
            total_quantity = 0.0
            total_weight = 0.0

            for line in invoice_line_lot.stock_move_line_id:
                if line.product_uom_id == uom_weight:
                    total_weight += line.quantity
                    total_cost_weight += line.price_subtotal
                else:
                    total_quantity += line.quantity
                    total_cost_quantity += line.price_subtotal

            if total_weight:
                product.current_cost_price = total_cost_weight / total_weight
            elif total_quantity:
                product.current_cost_price = total_cost_quantity / total_quantity
            else:
                product.current_cost_price = 0.0

    def compute_cost_price(self):
        """ Compute all price """
        self.compute_average_cost_price()
        self._compute_standard_price()

    @api.depends('default_code')
    def compute_gestion_affinage(self):
        """ Define if this cheese has a maturing managing """
        for product in self:
            gestion_affinage = False
            if product.default_code and product.default_code[-1] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                gestion_affinage = True
            product.gestion_affinage = gestion_affinage

    def get_maturity_product(self):
        """ return all maturing of product """
        res = {}
        for product in self:
            res[product.id] = []
            if product.gestion_affinage:
                fuzzy_code = product.default_code[:-1]
                product_ids = self.env['product.product'].search([('default_code', 'like', fuzzy_code),
                                        ('default_code', '!=', product.default_code)], order='default_code')
                for product_check in product_ids:
                    if product_check.gestion_affinage and self._name == 'product.product':
                        res[product.id].append(product_check)
                    elif product_check.gestion_affinage and self._name == 'product.template':
                        res[product.id].append(product_check.product_tmpl_id)
        return res

    def _compute_service_type(self):
        """ only one case manually"""
        self.service_type = 'manual'

    def _compute_invoice_policy(self):
        """ Define invoice policy"""
        for product in self:
            product.invoice_policy = "delivery"

    @api.depends('list_price', 'weight', 'uos_id', 'bom_ids',
                 'bom_ids.base_unit_count', 'bom_ids.type', 'bom_ids.base_product_id')
    def compute_package(self):
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for product in self:
            if product.bom_ids:
                # Case when there is a package
                bom = product.bom_ids[0]
                product.base_unit_count = bom.base_unit_count or 1.0
                product.base_product_tmpl_id = bom.base_product_id.product_tmpl_id or False
            else:
                product.base_unit_count = 1.0
                product.base_product_tmpl_id = False

            product.base_unit_price = product.list_price

            if product.uos_id == uom_weight:
                # Case when the price in kg
                product.base_package_price = product.weight * product.list_price
            else:
                product.base_package_price = product.list_price * (product.base_unit_count or 1.0)

    @api.depends('uos_id', 'base_unit_id.name')
    def _compute_base_unit_name(self):
        for template in self:
            template.base_unit_name = template.base_unit_id.name or template.uos_id.name

    def no_route_ids(self):
        """ update all route_ids"""
        self.route_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(f'------create-----product.template----------------------\n{vals_list}')
        return super().create(vals_list)

    def update_standard_price(self):
        """ update """
        for product in self.product_variant_ids:
            valuation_vals = {
                'product_id': product.id,
                'company_id': 1,
                'description': 'Manual update: ' + product.name,
                'quantity': product.qty_available,
                'unit_cost': product.standard_price,
                'value': product.qty_available * product.standard_price,
                'remaining_qty': product.qty_available,
            }
            print('---------------valuation_vals----------------', valuation_vals, product.standard_price)
            valuation = self.env['stock.valuation.layer'].create(valuation_vals)
            # action_revaluation