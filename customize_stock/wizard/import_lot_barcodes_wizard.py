# models/import_lot_barcodes_wizard.py
from odoo import models, fields
from odoo.exceptions import UserError
import base64
import io
import pandas as pd
import logging

_logger = logging.getLogger(__name__)


class ImportLotBarcodesWizard(models.TransientModel):
    _name = "import.lot.barcodes.wizard"
    _description = "Import des codes barres sur les lots depuis Excel"

    excel_file = fields.Binary("Fichier Excel")
    file_name = fields.Char("Nom du fichier")

    def action_import_lots(self):
        """Importe les champs barcode / barcode_ext / barcode_ext2
           sur stock.lot en se basant sur la colonne 'Référence interne' du fichier Excel.
        """
        if not self.excel_file:
            raise UserError("Veuillez sélectionner un fichier Excel.")

        # Lecture du fichier
        try:
            data = base64.b64decode(self.excel_file)
            df = pd.read_excel(io.BytesIO(data), dtype=str)
        except Exception as e:
            raise UserError(f"Impossible de lire le fichier Excel : {e}")

        # Colonnes attendues (exactement celles de ton fichier)
        required_cols = [
            "Référence interne",
            "Code barres",
            "Code barre (externe)",
            "Barcode (DIGI)",
        ]
        for col in required_cols:
            if col not in df.columns:
                raise UserError(
                    f"La colonne '{col}' est absente du fichier Excel. "
                    f"Colonnes trouvées : {list(df.columns)}"
                )

        updated = 0
        not_found = []

        for idx, row in df.iterrows():
            ref = (row["Référence interne"] or "").strip()
            if not ref:
                continue

            lot = self.env["stock.lot"].search([("ref", "=", ref)], limit=1)
            if not lot:
                not_found.append(ref)
                continue

            vals = {
                "barcode": (row["Code barres"] or "").strip() or False,
                "barcode_ext": (row["Code barre (externe)"] or "").strip() or False,
                "barcode_ext2": (row["Barcode (DIGI)"] or "").strip() or False,
            }
            lot.write(vals)
            updated += 1

        _logger.info(
            "IMPORT_LOT_BARCODE - %s lots mis à jour, %s références introuvables",
            updated,
            len(not_found),
        )

        # Retour : petite notif
        message = f"{updated} lots mis à jour."
        if not_found:
            message += f" {len(not_found)} références internes non trouvées."

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Import des lots terminé",
                "message": message,
                "type": "success" if not not_found else "warning",
            },
        }
