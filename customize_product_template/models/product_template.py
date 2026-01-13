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

    uos_po_id = fields.Many2one('uom.uom', string="Unité d'achat fournisseur")

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

    cost_price_date = fields.Datetime('last cost price compute', default=fields.Datetime.now())
    average_cost_price = fields.Float(
        string="Average Purchase (6 month)",
        help="Average purchase price based on last 6 months vendor's invoices",
        compute="compute_average_cost_price",
        store=True
    )
    average_weight = fields.Float(
        string="Average weight (6 month)",
        help="Average weight based on last 6 months vendor's invoices",
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

    transport_cost = fields.Float(
        string="Coût transport",
        help="Coût de transport unitaire à intégrer dans la valorisation du stock."
    )

    transformation_cost = fields.Float(
        string="Transformation Cost (€)",
        help="Cost of cutting and packaging the product in €"
    )

    total_cost_price = fields.Float(
        string="Total Cost Price",
        help="Average Purchase Price + Refinement, Cutting and Transformation Costs"
    )

    manual_stock_valuation = fields.Boolean(
        related='categ_id.manual_stock_valuation',
        string="Valorisation manuelle du stock (Excel)",
        store=True,
        readonly=False,
        help="Repris depuis la catégorie. Si cochée : la valorisation ignore les OF et utilise les valeurs Excel / prix de revient."
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
    

    global_component_quantity = fields.Float(
        string="Global Component Quantity",
        compute="_compute_global_component_quantity",
        store=True,
        help="Total quantity of all final components used in the product BOM."
    )

    def _compute_global_component_quantity(self):
        for tmpl in self:
            tmpl.global_component_quantity = sum(
                tmpl.component_price.mapped('quantity')
            )

    component_price = fields.One2many('product.component.hierarchy', 'product_tmpl_id', string='Component')
    exclude_from_intrastat = fields.Boolean('Exclure de la déclaration DEB')


    transformation_tmpl_ids_path = fields.Text(
        string="Transformation (Template IDs)",
        compute="_compute_transformation_paths",
        store=False,
    )

    transformation_variant_ids_path = fields.Text(
        string="Transformation (Variant IDs)",
        compute="_compute_transformation_paths",
        store=False,
    )

    def _compute_transformation_paths(self):
        Bom = self.env['mrp.bom']
        cache = {}  # {tmpl_id: [ [tmpl_id, tmpl_id, ...], ... ]}

        def walk(tmpl, visited):
            if not tmpl:
                return []
            tmpl = tmpl.exists()
            if not tmpl:
                return []
            tmpl.ensure_one()

            if tmpl.id in visited:
                return []

            if tmpl.id in cache:
                return cache[tmpl.id]

            visited = visited | {tmpl.id}

            bom = Bom.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
            if not bom or not bom.bom_line_ids:
                cache[tmpl.id] = []
                return []

            paths = []
            for line in bom.bom_line_ids:
                comp_tmpl = line.product_tmpl_id
                if not comp_tmpl:
                    continue
                comp_tmpl = comp_tmpl.exists()
                if not comp_tmpl:
                    continue
                comp_tmpl.ensure_one()

                subpaths = walk(comp_tmpl, visited)
                if subpaths:
                    for sp in subpaths:
                        paths.append([int(comp_tmpl.id)] + [int(x) for x in sp])
                else:
                    paths.append([int(comp_tmpl.id)])

            cache[tmpl.id] = paths
            return paths

        def tmpl_id_to_variant_id(tmpl_id):
            tmpl = self.env['product.template'].browse(tmpl_id).exists()
            if not tmpl:
                return False
            tmpl.ensure_one()
            # mono-variant => product_variant_id, sinon 1ère variante
            variant = tmpl.product_variant_id or tmpl.product_variant_ids[:1]
            return int(variant.id) if variant else False

        for rec in self:
            rec = rec.exists()
            if not rec:
                rec.transformation_tmpl_ids_path = ""
                rec.transformation_variant_ids_path = ""
                continue
            rec.ensure_one()

            tmpl_paths = walk(rec, set())

            # 1) Champ Template IDs : "12;45;78 | 12;90"
            rec.transformation_tmpl_ids_path = " | ".join(
                ";".join(str(x) for x in path)
                for path in tmpl_paths
                if path
            ) if tmpl_paths else ""

            # 2) Champ Variant IDs : conversion template -> product.product
            variant_paths = []
            for path in tmpl_paths:
                vpath = []
                for tmpl_id in path:
                    vid = tmpl_id_to_variant_id(tmpl_id)
                    if vid:
                        vpath.append(vid)
                if vpath:
                    variant_paths.append(vpath)

            rec.transformation_variant_ids_path = " | ".join(
                ";".join(str(x) for x in vpath)
                for vpath in variant_paths
            ) if variant_paths else ""
            
    
    transformation_ids_path = fields.Text(
        string="Transformation (IDs)",
        compute="_compute_transformation_ids_path",
        store=False,
    )

    def _compute_transformation_ids_path(self):
        Bom = self.env['mrp.bom']
        cache = {}  # {tmpl_id: [ [int,int,...], ... ]}

        def walk(tmpl, visited):
            # tmpl doit être un record unique
            if not tmpl:
                return []
            tmpl = tmpl.sudo().exists()
            if not tmpl:
                return []
            tmpl.ensure_one()

            if tmpl.id in visited:
                return []

            if tmpl.id in cache:
                return cache[tmpl.id]

            visited = visited | {tmpl.id}

            # Récupère 1 BOM pertinente (à ajuster si tu as plusieurs BOM)
            bom = Bom.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
            if not bom or not bom.bom_line_ids:
                cache[tmpl.id] = []
                return []

            paths = []
            for line in bom.bom_line_ids:
                comp_tmpl = line.product_tmpl_id
                if not comp_tmpl:
                    continue
                comp_tmpl = comp_tmpl.exists()
                if not comp_tmpl:
                    continue
                comp_tmpl.ensure_one()

                subpaths = walk(comp_tmpl, visited)
                if subpaths:
                    # on préfixe le chemin par l'id du composant template
                    for sp in subpaths:
                        # sp doit être une liste d'int, on force
                        paths.append([int(comp_tmpl.id)] + [int(x) for x in sp])
                else:
                    # feuille
                    paths.append([int(comp_tmpl.id)])

            cache[tmpl.id] = paths
            return paths

        for rec in self:
            rec = rec.exists()
            if not rec:
                rec.transformation_ids_path = ""
                continue
            rec.ensure_one()

            all_paths = walk(rec, set())

            # format: "id1;id2;id3 | idA;idB"
            rec.transformation_ids_path = " | ".join(
                ";".join(str(x) for x in path)
                for path in all_paths
                if path
            ) if all_paths else ""


    @api.model
    def get_coef_workshop_cost(self):
        """ return coef to apply between workshop_cost_price and total_cost_price """
        coef_workshop_cost = float(self.env["ir.config_parameter"].sudo().get_param("customize_account.coef_workshop_cost", '1.12'))
        return coef_workshop_cost


    @api.onchange('categ_id')
    def onchange_categ_id(self):
        """ get configuration on categ """
        for product in self:
            product.tracking = product.categ_id.tracking



    @api.depends('total_cost_price', 'weight', 'uos_id')
    def _compute_standard_price(self):
        """ Compute the standard price """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        coef_workshop_cost = self.get_coef_workshop_cost()

        for product in self:
            product.workshop_cost_price = product.total_cost_price * coef_workshop_cost

            if product.uos_id == uom_weight and product.weight:
                standard_price = product.workshop_cost_price * product.weight
            elif product.uos_id == uom_weight and not product.weight:
                standard_price = 0.0
            else:
                standard_price = product.workshop_cost_price

            product.standard_price = standard_price

    def compute_average_cost_price(self):
        """ futur Compute the average cost price """
        for product in self:
            product.average_cost_price = 0.0
            product.average_weight = 0.0

    def compute_current_cost_price(self):
        """ futur compute current stock value """
        for product in self:
            product.current_cost_price = product.average_cost_price

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
            valuation = self.env['stock.valuation.layer'].create(valuation_vals)
            # action_revaluation