# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


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

    @api.depends('categ_id.tracking', 'categ_id.type', 'categ_id.detailed_type', 'categ_id.use_expiration_date')
    def update_categ_value(self):
        """ Update value based on categ value"""
        for product in self:
            if product.categ_id:
                product.tracking = product.categ_id.tracking
                product.type = product.categ_id.type
                product.detailed_type = product.categ_id.detailed_type
                product.use_expiration_date = product.categ_id.use_expiration_date
            else:
                product.tracking = 'none'
                product.type = 'product'
                product.detailed_type = 'product'
                product.use_expiration_date = False

    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')],
        string="Tracking",  compute="update_categ_value", store=True,
        help="Ensure the traceability of a storable product in your warehouse.")

    type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type", compute="update_categ_value", store=True)

    detailed_type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type",  compute="update_categ_value", store=True)

    use_expiration_date = fields.Boolean(string="Use expiration date", compute="update_categ_value", store=True)

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
    allergen = fields.Many2many('product.allergen', 'allereg_reel', string="Allergen" )
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

    life_date = fields.Boolean(string='DLC : End of Life Date')
    use_date = fields.Boolean(string='DDM : Best before Date')

    to_weight = fields.Boolean(string='to weight')
    tare = fields.Float(string='Tare', help='Tare')
    weight_gross = fields.Float(string='Gross Weight',help='The gross weight in Kg.')
    format_etiquette =  fields.Char('Format d\'etiquette', size=128)
    to_label = fields.Boolean(string='to label')
    gestion_affinage = fields.Boolean(string='Refining management')
    to_personnalize = fields.Boolean(string='Customer specifity')

    # WEB description
    web_historic = fields.Html('Historic')
    web_manufacture = fields.Html('Manufacture')
    web_tasting = fields.Html('Tasting')

    base_unit_count = fields.Float('Unit Count', compute="compute_package", inverse=False, store=True, default=1.0,
        help="Number of unit in the package.")

    base_unit_price = fields.Float("Price Per Unit", compute="compute_package", store=True, default=0.0,
        help="Price of unit in the package.")
    # inverse='_set_base_unit_price'

    base_product_tmpl_id = fields.Many2one("product.template", string="Unit product",
                                        compute="compute_package", store=True)

    base_unit_name = fields.Char(compute='_compute_base_unit_name',
                                 help='Displays the custom unit for the products if defined or the selected unit of measure otherwise.')

    @api.depends('list_price', 'uos_id', 'bom_ids', 'bom_ids.base_unit_count')
    def compute_package(self):
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for product in self:
            if not product.id:
                product.base_unit_count = 1.0
                product.base_product_tmpl_id = False
                product.base_unit_price = 0.0
            else:
                if product.bom_ids:
                    # Case when there is a package
                    bom = product.bom_ids[0]
                    product.base_unit_count = bom.base_unit_count or 1.0
                    product.base_product_tmpl_id = bom.base_product_id.product_tmpl_id or False
                else:
                    product.base_unit_count = 1.0
                    product.base_product_tmpl_id = False

                if product.uos_id == uom_weight:
                    # Case when the price in kg
                    product.base_unit_price = product.list_price
                else:
                    product.base_unit_price = product.list_price / (product.base_unit_count or 1.0)

    def _get_base_unit_price(self, price):
        self.ensure_one()
        return self.base_unit_price

    @api.depends('uos_id', 'base_unit_id.name')
    def _compute_base_unit_name(self):
        for template in self:
            template.base_unit_name = template.base_unit_id.name or template.uos_id.name

    def no_route_ids(self):
        """ update all route_ids"""
        self.route_ids = False

