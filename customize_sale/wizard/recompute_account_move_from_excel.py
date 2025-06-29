from odoo import models, fields, api
import base64
import io
import pandas as pd
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class RecomputeAccountMoveFromExcel(models.TransientModel):
    _name = 'recompute.account.move.from.excel'
    _description = 'Recalcul des montants de factures depuis fichier Excel'

    excel_file = fields.Binary(string="Fichier Excel", required=True)
    file_name = fields.Char(string="Nom du fichier")

    def action_recompute_moves(self):
        if not self.excel_file:
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
