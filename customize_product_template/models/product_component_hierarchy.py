from odoo import fields, models, tools

class ProductComponentHierarchy(models.Model):
    _name = "product.component.hierarchy"
    _description = "Product Component Hierarchy"
    _auto = False  # Indique que ce modèle est basé sur une vue SQL
    _table = "product_component_hierarchy"

    _depends = {
        'mrp.bom': ['product_tmpl_id', 'product_id'],
        'mrp.bom.line': ['product_tmpl_id', 'product_id', 'product_qty'],
    }

    product_tmpl_id = fields.Many2one('product.template', string="Product Template", readonly=True)
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    composant_tmpl_id = fields.Many2one('product.template', string="Component Template", readonly=True)
    composant_id = fields.Many2one('product.product', string="Component", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    level = fields.Integer(string="Level", readonly=True)
    last_level = fields.Boolean(string="Is Last Level", readonly=True)

    @property
    def _table_query(self):
        """Définit la requête SQL de la vue"""
        return """
        WITH RECURSIVE component_hierarchy AS (
            -- Niveau initial : récupérer les composants directs du produit
            SELECT 
                bom.product_tmpl_id AS product_tmpl_id,
                bom.product_id AS product_id,
                line.product_id AS composant_id,
                line.product_tmpl_id AS composant_tmpl_id,
                line.product_qty AS quantity,
                1 AS level, -- Niveau initial
                NOT EXISTS (
                    SELECT 1
                    FROM mrp_bom sub_bom
                    WHERE sub_bom.product_id = line.product_id
                ) AS last_level -- Vérifie si le composant n'a pas de sous-nomenclature
            FROM 
                mrp_bom bom
            JOIN 
                mrp_bom_line line ON bom.id = line.bom_id

            UNION ALL

            -- Niveau récursif : parcourir les sous-composants
            SELECT 
                ch.product_tmpl_id AS product_tmpl_id,
                ch.product_id AS product_id,
                line.product_id AS composant_id,
                line.product_tmpl_id AS composant_tmpl_id,
                ch.quantity * line.product_qty AS quantity,
                ch.level + 1 AS level, -- Incrémenter le niveau
                NOT EXISTS (
                    SELECT 1
                    FROM mrp_bom sub_bom
                    WHERE sub_bom.product_id = line.product_id
                ) AS last_level -- Vérifie si le composant n'a pas de sous-nomenclature
            FROM 
                component_hierarchy ch
            JOIN 
                mrp_bom bom ON ch.composant_id = bom.product_id
            JOIN 
                mrp_bom_line line ON bom.id = line.bom_id
        )
        SELECT 
            product_id * 10000 + composant_id as id,
            product_tmpl_id,
            product_id,
            composant_tmpl_id,
            composant_id,
            quantity,
            level,
            last_level
        FROM 
            component_hierarchy
        WHERE
            last_level is true
        """

    def init(self):
        """Créer la vue SQL si elle n'existe pas déjà"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                {self._table_query}
            )
        """)

