from odoo import models, fields, api
import base64
import io
import pandas as pd
from odoo.exceptions import UserError
import logging
import re
from fractions import Fraction
_logger = logging.getLogger(__name__)

class RecomputeAccountMoveFromExcel(models.TransientModel):
    _name = 'recompute.account.move.from.excel'
    _description = 'Recalcul des montants de factures depuis fichier Excel'

    # Premier fichier
    excel_file_1 = fields.Binary(string="Factures GB montants € et £ erronés")
    file_name_1 = fields.Char(string="Nom du fichier (1)")

    # Deuxième fichier
    excel_file_2 = fields.Binary(string="Factures GB montants € erronés")
    file_name_2 = fields.Char(string="Nom du fichier (2)")

    def _get_colis_factor(self, name):
        """
        Détecte automatiquement le facteur colis dans un libellé produit.
        Gère :
        - "colis 6", "colis 2x1/2", "colis 3 x 4"
        - suffixes "x12", "x 6", "x4"
        - formats cosv 12 / cosv12 / cosv 4 / cosv4
        - cas ajoutés par Dkgroup
        """
        name = (name or '').lower().replace('.', ' ').strip()

        # --- 1️⃣ Format explicite : "colis 6", "colis 2x1/2"
        match_colis = re.search(r'colis\s*([\d x\/]+)', name)
        if match_colis:
            raw = match_colis.group(1).strip()
            try:
                if 'x' in raw:
                    parts = re.split(r'\s*x\s*', raw)
                    values = [float(Fraction(p.strip())) for p in parts]
                    return float(eval('*'.join(str(v) for v in values)))
                else:
                    return float(Fraction(raw))
            except Exception:
                return 1.0

        # --- 2️⃣ Format implicite : "x12", "x6", "x 4" en fin de libellé
        match_x = re.search(r'x\s*(\d+)$', name)
        if match_x:
            return float(match_x.group(1))

        # --- 3️⃣ Format cosv 12 / cosv12 (tous tes nouveaux cas)
        match_cosv = re.search(r'cosv\s*(\d+)', name)
        if match_cosv:
            return float(match_cosv.group(1))

        # --- Aucun format reconnu → facteur 1
        return 1.0

    def action_recompute_moves(self):

        if not self.excel_file_1 and not self.excel_file_2:
            raise UserError("Veuillez importer au moins un des deux fichiers Excel pour lancer le traitement.")

        df1 = df2 = None

        # Traitement fichier 1
        if self.excel_file_1:

            file_data_1 = base64.b64decode(self.excel_file_1)
            df1 = pd.read_excel(io.BytesIO(file_data_1), skiprows=0)

            # Renommer les colonnes proprement
            df1.columns = [
                "Numéro",
                "Adresse de livraison",
                "Date de facturation",
                "V7 €",
                "V7 £",
                "€",
                "£"
            ]

            products_seen = set()
            # Parcours de chaque ligne du fichier
            for index, row in df1.iterrows():
                ref = str(row["Numéro"]).strip()
                
                # Recherche de la facture dans Odoo
                move = self.env['account.move'].search([('name', '=', ref)], limit=1)
                
                for line in move.invoice_line_ids:
                    product_name = (line.product_id.name or "").lower()

                    # ✅ Ajout de la contrainte : uniquement si unité = U (id=1)
                    if line.product_uom_id.id != 1:
                        continue

                    # Vérifie s'il y a "colis" OU un "xN" à la fin
                    #if "colis" not in product_name and not re.search(r'x\s*\d+$', product_name):
                    #    continue  # on ignore cette ligne

                    factor = self._get_colis_factor(product_name)
                    if factor <= 0 or factor == 1:
                        continue

                    products_seen.add(f"{line.product_id.name} (factor={factor})")
                    
                    #_logger.info(f"WARNING_DKGROUP product_name : {line.product_id.name} factor {factor}")
                    
                    #continue

                    line.uom_qty = line.uom_qty / factor if factor > 0 else qty
                    line.quantity = line.quantity / factor
                    _logger.info(f"WARNING_DKGROUP product_id : {line.product_id.name}")
                    _logger.info(f"WARNING_DKGROUP uom_qty : {line.uom_qty}")

                if not move:
                    _logger.warning(f"Aucune facture trouvée dans Odoo pour : {ref}")
                    continue

            """if products_seen:
                final_list = sorted(products_seen)
                _logger.warning(f" WARNING_DKGROUP Produits rencontrés : {final_list}")
            else:
                _logger.warning("Aucun produit rencontré dans le traitement.")"""

        # Traitement uniquement de df2 ici pour l'exemple
        if self.excel_file_2:
         
            file_data_2 = base64.b64decode(self.excel_file_2)
            df2 = pd.read_excel(io.BytesIO(file_data_2), skiprows=0)

            # Renommer les colonnes proprement
            df2.columns = [
                "Numéro",
                "Adresse de livraison",
                "Date de facturation",
                "V7 €",
                "V7 £",
                "€",
                "£"
            ]

            # Parcours de chaque ligne
            _logger.info("WARNING_DKGROUP df2 : %s", str(df2))
            for index, row in df2.iterrows():
                ref = str(row["Numéro"]).strip()
                _logger.info("WARNING_DKGROUP ref : %s", str(ref))

                montant_excel = float(str(row["V7 €"]).replace(",", "."))
                montant_ajuste = float(str(row["€"]).replace(",", "."))

                _logger.info("WARNING_DKGROUP ref : %s", str(ref))
                move = self.env['account.move'].search([('name', '=', ref)], limit=1)
                zero_lines = move.line_ids.filtered(lambda l: not l.debit and not l.credit)
                for line in zero_lines:
                    origin_price_unit = line.price_unit
                    line.price_unit = origin_price_unit+1
                    line.price_unit = origin_price_unit

        return True















        if not self.excel_file_1:
            raise UserError("Veuillez importer un fichier Excel contenant les numéros de facture.")

        try:
            file_data = base64.b64decode(self.excel_file)
            df = pd.read_excel(io.BytesIO(file_data))
        except Exception as e:
            raise UserError(f"Erreur de lecture du fichier : {e}")

        # Log des colonnes pour debug
        _logger.info("WARNING_DKGROUP Colonnes détectées : %s", list(df.columns))

        # Vérification colonne obligatoire
        if 'Numéro' not in df.columns:
            raise UserError("La colonne 'Numéro' est absente du fichier Excel.")

        # Extraction des numéros de facture
        facture_refs = df['Numéro'].dropna().astype(str).unique().tolist()
        _logger.info("WARNING_DKGROUP Facture %s ", str(len(facture_refs)))

        #facture_refs = ['F504882']
        moves = self.env['account.move'].search([('name', 'in', facture_refs)])
        if not moves:
            raise UserError("Aucune facture trouvée dans Odoo avec les références fournies.")

        errors = []
        # Diviser les moves en batchs de 200
        batch_size = 200
        for i in range(0, len(moves), batch_size):
            batch = moves[i:i + batch_size]
            for move in batch:
                try:
                    if move.state == 'posted':
                        move.button_draft()         # Remise en brouillon
                        move._compute_amount()      # Recalcule les montants
                        move.action_post()          # Revalidation
                except Exception as e:
                    errors.append(f"{move.name}: {str(e)}")

        message = f"{len(moves)} factures traitées avec succès."
        if errors:
            message += f"\n⚠️ {len(errors)} erreurs :\n" + "\n".join(errors[:10])  # Limite à 10 erreurs

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Résultat du recalcul',
                'message': message,
                'type': 'warning' if errors else 'success',
            }
        }
