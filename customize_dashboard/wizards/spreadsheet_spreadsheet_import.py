# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models,tools
from collections import defaultdict
from odoo.exceptions import UserError
import calendar
import base64
import json
import logging
import string
import re
from dateutil.relativedelta import relativedelta
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo.osv import expression

class SpreadsheetSpreadsheetImportInherit(models.TransientModel):
    _inherit = "spreadsheet.spreadsheet.import"

    is_comparison_mode = fields.Boolean(
        string="Mode comparaison actif",
        compute="_compute_is_comparison_mode",
        store=False  # Pas besoin de stocker sauf si tu veux filtrer en SQL
    )
    
    @api.depends('import_data')
    def _compute_is_comparison_mode(self):
        for record in self:
            comparison = record.import_data.get("searchParams", {}).get("comparison") if record.import_data else None
            record.is_comparison_mode = bool(comparison and comparison.get("domains"))

    
    @api.onchange('is_comparison_mode')
    def _onchange_is_comparison_mode(self):
        if self.is_comparison_mode:
            return {'domain': {'mode_id': [('code', 'in', ['new', 'dashboard_spreadsheet'])]}}
        else:
            return {'domain': {'mode_id': []}}

    def _is_comparison_mode(self):
        """
        Détecte si le mode comparaison est actif en vérifiant que les domaines de comparaison existent.
        """
        comparison = self.import_data.get("searchParams", {}).get("comparison")
        return bool(comparison and comparison.get("domains"))
    
    def _column_letter(self, n):
        """Convertit un index de colonne en lettre de colonne Excel (A, B, ..., Z, AA, AB, ...)"""
        result = ''
        while n >= 0:
            result = chr(n % 26 + 65) + result
            n = n // 26 - 1
        return result

    def _build_pivots_from_periods(self, periods, row_group_bys, col_group_bys, search_context,base_domain=None):
        """
        Construit dynamiquement les pivots Odoo à partir des périodes.
        :param periods: liste des périodes (ex: ["2024-T1", "2025-01"])
        :param row_group_bys: champs de regroupement ligne
        :param col_group_bys: champs de regroupement colonne
        :param search_context: contexte de recherche pour le pivot
        :return: (dict: pivots, int: pivotNextId)
        """
        pivots = {}
        pivot_id = 1
        domains = []
        base_domain = base_domain or []

        for period in periods:
            try:
                # Format 'YYYY-MM'
                if "-" in period and period.split("-")[1].isdigit():
                    date_start = datetime.strptime(period, "%Y-%m")
                    date_end = date_start + relativedelta(months=3) - relativedelta(days=1)

                # Format 'YYYY-T1' or 'YYYY-Q1'
                elif "-" in period and period.split("-")[1][0] in ["T", "Q"]:
                    year, quarter = period.split("-")
                    month_start = (int(quarter[1]) - 1) * 3 + 1
                    date_start = datetime(int(year), month_start, 1)
                    date_end = date_start + relativedelta(months=3) - relativedelta(days=1)
                # Format 'T1 YYYY' or 'Q1 YYYY'
                elif " " in period and period.split(" ")[0][0] in ["T", "Q"]:
                    quarter, year = period.split(" ")
                    month_start = (int(quarter[1]) - 1) * 3 + 1
                    date_start = datetime(int(year), month_start, 1)
                    date_end = date_start + relativedelta(months=3) - relativedelta(days=1)

                # Format 'YYYY' → année complète
                elif re.fullmatch(r"\d{4}", period):
                    date_start = datetime(int(period), 1, 1)
                    date_end = datetime(int(period), 12, 31)
                    _logger.info("Période interprétée comme année complète : %s à %s", date_start, date_end)

                else:
                    _logger.warning("Format de période non reconnu, ignoré : %s", period)
                    continue

                period_domain = base_domain + [
                    #["move_type", "in", ["out_invoice", "out_refund"]],
                    ["invoice_date", ">=", date_start.strftime("%Y-%m-%d")],
                    ["invoice_date", "<=", date_end.strftime("%Y-%m-%d")]
                ]

                pivot = {
                    "id": str(pivot_id),
                    "name": f"Pivot {period}",
                    "model": "account.invoice.report",
                    "measures": [{"field": "price_subtotal"}],
                    "domain": period_domain,
                    "rowGroupBys": row_group_bys,
                    "colGroupBys": col_group_bys,
                    "context": search_context,
                    "sortedColumn": None,
                    "fieldMatching": {}
                }

                pivots[str(pivot_id)] = pivot
                domains.append(period_domain)
                pivot_id += 1

            except Exception:
                continue  # Ignore les erreurs pour chaque période

        return pivots, pivot_id, domains


    def _get_row_group_values(self, row_group_bys, search_params):
        """
        Récupère dynamiquement les valeurs distinctes de regroupement pour les lignes de la vue pivot,
        en nettoyant les floats en entiers et en les triant dans l'ordre naturel.

        :param row_group_bys: liste des champs de regroupement ligne (ex: ["month"])
        :param search_params: import_data["searchParams"]
        :return: liste triée des valeurs uniques sous forme de string (ex: ["1", "2", ..., "14"])
        """
        if not row_group_bys:
            return []

        row_field = row_group_bys[0]
        base_domain = search_params.get("domain", [])
        origin_domains = [
            base_domain + comp.get("arrayRepr", [])
            for comp in search_params.get("comparison", {}).get("domains", [])
        ]

        row_values = set()
        for domain in origin_domains:
            values = self.env["account.invoice.report"].read_group(
                domain, [row_field], [row_field]
            )
            for v in values:
                val = v.get(row_field)
                if val is not None:
                    try:
                        row_values.add(int(float(val)))  # cast propre depuis float/str
                    except (ValueError, TypeError):
                        pass  # on ignore les cas douteux

        return [str(v) for v in sorted(row_values)]


    def _get_col_group_values(self, col_group_bys, fields, domains=None):
        """
        Récupère les valeurs distinctes du champ colonne du pivot, en respectant les domaines des différentes périodes.
        - col_group_bys : liste des champs group by colonne (ex: ['state'], ['team_id'])
        - fields : le dict des fields Odoo (import_data['metaData']['fields'])
        - domains : liste de domaines (un par période, optionnel)
        Retourne: [{"id": x, "label": y}, ...]
        """
        col_values_set = []

        if not col_group_bys:
            return col_values_set

        col_group_by = col_group_bys[0]
        field = fields.get(col_group_by, {})
        if not field:
            return col_values_set

        present_vals = set()
        if domains:
            # On lit les valeurs vraiment utilisées dans AU MOINS une période/pivot
            for dom in domains:
                if field.get('type') == 'selection':
                    results = self.env["account.invoice.report"].read_group(
                        dom, [col_group_by], [col_group_by]
                    )
                    present_vals.update(
                        r[col_group_by]
                        for r in results
                        if r.get(col_group_by) is not None
                    )
                elif field.get('type') == 'many2one':
                    results = self.env["account.invoice.report"].read_group(
                        dom, [col_group_by], [col_group_by]
                    )
                    present_vals.update(
                        r[col_group_by][0]
                        for r in results
                        if r.get(col_group_by)
                    )
            # Formatage final selon type de champ
            if field.get('type') == 'selection':
                col_values_set = [
                    {"id": val, "label": label}
                    for val, label in field.get("selection", [])
                    if val in present_vals
                ]
                # Si c'est le champ 'state', on veut commencer par 'posted'
                if col_group_by == "state":
                    # On trie pour avoir 'posted' en premier, puis le reste
                    col_values_set = sorted(
                        col_values_set,
                        key=lambda x: 0 if x["id"] == "posted" else 1
                    )
            elif field.get('type') == 'many2one':
                relation_model = field['relation']
                # Respecte l'ordre alpha du display_name
                records = self.env[relation_model].browse(list(present_vals)).sorted('display_name')
                col_values_set = [{"id": rec.id, "label": rec.display_name} for rec in records]
        else:
            # Fallback : on affiche tout
            if field.get('type') == 'selection':
                col_values_set = [
                    {"id": val, "label": label}
                    for val, label in field.get("selection", [])
                ]
            elif field.get('type') == 'many2one':
                relation_model = field['relation']
                records = self.env[relation_model].search([])
                col_values_set = [{"id": rec.id, "label": rec.display_name} for rec in records]

        return col_values_set

    def _generate_comparison_spreadsheet_json(self):
        import_data = self.import_data
        meta_data = import_data["metaData"]
        title = meta_data.get("title", "Analyse Comparée")
        fields = meta_data.get("fields", {})
        periods = sorted(meta_data.get("origins", []))
        measures = meta_data.get("activeMeasures", [])
        search_params = import_data.get("searchParams", {})

        col_group_bys = (
            meta_data.get("expandedColGroupBys")
            or meta_data.get("colGroupBys")
            or search_params.get("context", {}).get("pivot_column_groupby", [])
        )
        col_group_bys = col_group_bys or []
        has_columns = bool(col_group_bys)

        row_group_bys = (
            meta_data.get("expandedRowGroupBys")
            or meta_data.get("rowGroupBys")
            or search_params.get("context", {}).get("pivot_row_groupby", [])
        )

        allowed_labels = ["Mois", "Semaine"]
        for row_group_by in row_group_bys:
            label = fields.get(row_group_by, {}).get("string")
            if label not in allowed_labels:
                raise UserError(
                    f"Filtre '{label}' interdit en ligne de comparaison. Utilisez uniquement : {', '.join(allowed_labels)}."
                )

        pivots, pivotNextId, domains = self._build_pivots_from_periods(
            periods,
            row_group_bys,
            col_group_bys,
            search_params.get("context", {}),
            search_params.get("domain", [])
        )

        row_values_set = self._get_row_group_values(row_group_bys, search_params)
        col_values_set = self._get_col_group_values(col_group_bys, fields, domains) if has_columns else []

        styles = {
            "1": {"bold": True, "fillColor": "#f2f2f2"},
            "2": {"fillColor": "#f2f2f2", "textColor": "#756f6f"},
            "3": {"bold": False, "italic": False, "underline": False, "textColor": "#000000", "fillColor": "#ffffff"},
            "4": {"textColor": "#d00000", "bold": True},
            "5": {"textColor": "#1c9c50", "bold": True},
        }

        conditional_formats = [
            {
                "id": "negative-variation",
                "rule": {
                    "type": "CellIsRule",
                    "operator": "LessThan",
                    "values": ["0"],
                    "style": {"textColor": "#FF0000", "fillColor": ""}
                },
                "ranges": []
            },
            {
                "id": "positive-variation",
                "rule": {
                    "type": "CellIsRule",
                    "operator": "GreaterThan",
                    "values": ["0"],
                    "style": {"textColor": "#6AA84F", "fillColor": ""}
                },
                "ranges": []
            }
        ]

        column_map = {}
        cells = {}
        row_start = 3
        row_index = row_start
        col_offset = 1
        col_state_width = 3
        pivot_mapping = {period: str(i + 1) for i, period in enumerate(periods)}

        if has_columns:
            for i, col_item in enumerate(col_values_set):
                col = col_offset + i * col_state_width
                column_map[col_item["id"]] = col
                cells[f"{self._column_letter(col)}1"] = {"content": col_item["label"], "style": 1}

            total_col = col_offset + len(col_values_set) * col_state_width
            cells[f"{self._column_letter(total_col)}1"] = {"content": "Total", "style": 1}

            for col_item in col_values_set:
                col = column_map[col_item["id"]]
                cells[f"{self._column_letter(col)}2"] = {"content": periods[0], "style": 2}
                cells[f"{self._column_letter(col + 1)}2"] = {"content": periods[1], "style": 2}
                cells[f"{self._column_letter(col + 2)}2"] = {"content": "Variation", "style": 2}

            cells[f"{self._column_letter(total_col)}2"] = {"content": periods[0], "style": 2}
            cells[f"{self._column_letter(total_col + 1)}2"] = {"content": periods[1], "style": 2}
            cells[f"{self._column_letter(total_col + 2)}2"] = {"content": "Variation", "style": 2}
        else:
            cells[f"{self._column_letter(col_offset)}1"] = {"content": "Valeur", "style": 1}
            cells[f"{self._column_letter(col_offset)}2"] = {"content": periods[0], "style": 2}
            cells[f"{self._column_letter(col_offset + 1)}2"] = {"content": periods[1], "style": 2}
            cells[f"{self._column_letter(col_offset + 2)}2"] = {"content": "Variation", "style": 2}

        for row_value in row_values_set:
            cells[f"A{row_index}"] = {"content": row_value, "style": 2}

            if has_columns:
                row_values = {}
                for col_item in col_values_set:
                    col_val = col_item["id"]
                    col = column_map[col_val]
                    pivot_id_1 = pivot_mapping.get(periods[0])
                    pivot_id_2 = pivot_mapping.get(periods[1])

                    c1 = f"{self._column_letter(col)}{row_index}"
                    c2 = f"{self._column_letter(col + 1)}{row_index}"
                    cv = f"{self._column_letter(col + 2)}{row_index}"

                    formula_1 = f'=IF(ODOO.PIVOT({pivot_id_1},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),ODOO.PIVOT({pivot_id_1},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),0)'
                    formula_2 = f'=IF(ODOO.PIVOT({pivot_id_2},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),ODOO.PIVOT({pivot_id_2},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),0)'

                    cells[c1] = {"content": formula_1, "format": "0.00"}
                    cells[c2] = {"content": formula_2, "format": "0.00"}
                    cells[cv] = {
                        "content": f"=IF({c1}=0, 0, ROUND(({c2}-{c1})/{c1}*100, 2))",
                        "format": "0.00"
                    }

                    conditional_formats[0]["ranges"].append(cv)
                    conditional_formats[1]["ranges"].append(cv)
                    row_values[col_val] = (c1, c2)

                tc1 = f"{self._column_letter(total_col)}{row_index}"
                tc2 = f"{self._column_letter(total_col + 1)}{row_index}"
                tcv = f"{self._column_letter(total_col + 2)}{row_index}"

                cells[tc1] = {"content": f"={'+'.join([v[0] for v in row_values.values()])}", "format": "0.00"}
                cells[tc2] = {"content": f"={'+'.join([v[1] for v in row_values.values()])}", "format": "0.00"}
                cells[tcv] = {
                    "content": f"=IF({tc1}=0, 0, ROUND(({tc2}-{tc1})/{tc1}*100, 2))",
                    "format": "0.00",
                    "style": 3
                }

                conditional_formats[0]["ranges"].append(tcv)
                conditional_formats[1]["ranges"].append(tcv)

            else:
                pivot_id_1 = pivot_mapping.get(periods[0])
                pivot_id_2 = pivot_mapping.get(periods[1])
                c1 = f"{self._column_letter(col_offset)}{row_index}"
                c2 = f"{self._column_letter(col_offset + 1)}{row_index}"
                cv = f"{self._column_letter(col_offset + 2)}{row_index}"

                formula_1 = f'=IF(ODOO.PIVOT({pivot_id_1},"price_subtotal","{row_group_bys[0]}","{row_value}"),ODOO.PIVOT({pivot_id_1},"price_subtotal","{row_group_bys[0]}","{row_value}"),0)'
                formula_2 = f'=IF(ODOO.PIVOT({pivot_id_2},"price_subtotal","{row_group_bys[0]}","{row_value}"),ODOO.PIVOT({pivot_id_2},"price_subtotal","{row_group_bys[0]}","{row_value}"),0)'

                cells[c1] = {"content": formula_1, "format": "0.00"}
                cells[c2] = {"content": formula_2, "format": "0.00"}
                cells[cv] = {
                    "content": f"=IF({c1}=0, 0, ROUND(({c2}-{c1})/{c1}*100, 2))",
                    "format": "0.00"
                }

                conditional_formats[0]["ranges"].append(cv)
                conditional_formats[1]["ranges"].append(cv)

            row_index += 1

        cells[f"A{row_index}"] = {"content": "Total", "style": 1}
        last_col = total_col + 3 if has_columns else col_offset + 3
        for col in range(col_offset, last_col):
            col_letter = self._column_letter(col)
            cells[f"{col_letter}{row_index}"] = {
                "content": f"=ROUND(SUM({col_letter}{row_start}:{col_letter}{row_index - 1}),2)",
                "format": "0.00"
            }

        return {
            "version": 12.5,
            "sheets": [{
                "id": "Sheet1",
                "name": "Sheet1",
                "colNumber": last_col + 1,
                "rowNumber": row_index + 10,
                "cells": cells,
                "conditionalFormats": conditional_formats,
                "merges": [],
                "figures": [],
                "filterTables": [],
                "rows": {},
                "cols": {},
                "areGridLinesVisible": True,
                "isVisible": True,
            }],
            "styles": styles,
            "entities": {},
            "formats": {},
            "borders": {},
            "revisionId": "SPREADSHEET_COMPARAISON_COMPLETE",
            "uniqueFigureIds": True,
            "odooVersion": 5,
            "globalFilters": [],
            "pivots": pivots,
            "pivotNextId": pivotNextId,
            "lists": {},
            "listNextId": 1,
            "chartOdooMenusReferences": {},
        }


    def _generate_comparison_spreadsheet_json_OLD(self):
        import_data = self.import_data
        meta_data = import_data["metaData"]
        title = meta_data.get("title", "Analyse Comparée")
        fields = meta_data.get("fields", {})
        periods = sorted(meta_data.get("origins", []))
        measures = meta_data.get("activeMeasures", [])
        search_params = import_data.get("searchParams", {})

        col_group_bys = (
            meta_data.get("expandedColGroupBys")
            or meta_data.get("colGroupBys")
            or search_params.get("context", {}).get("pivot_column_groupby", [])
        )

        row_group_bys = (
            meta_data.get("expandedRowGroupBys")
            or meta_data.get("rowGroupBys")
            or search_params.get("context", {}).get("pivot_row_groupby", [])
        )

        allowed_labels = ["Mois", "Semaine"]
        for row_group_by in row_group_bys:
            label = fields.get(row_group_by, {}).get("string")
            if label not in allowed_labels:
                raise UserError(
                    f"Filtre '{label}' interdit en ligne de comparaison. Utilisez uniquement : {', '.join(allowed_labels)}."
                )

        pivots, pivotNextId, domains = self._build_pivots_from_periods(
            periods,
            row_group_bys,
            col_group_bys,
            search_params.get("context", {}),
            search_params.get("domain", [])
        )
        _logger.info("WARNING_DKGROUP domains %s ", str(domains))
       
        """_logger.info("WARNING_DKGROUP row_group_bys %s ", str(row_group_bys))
        _logger.info("WARNING_DKGROUP col_group_bys %s ", str(col_group_bys))
        _logger.info("WARNING_DKGROUP search_params %s ", str(search_params))
        _logger.info("WARNING_DKGROUP pivots %s ", str(pivots))
        _logger.info("WARNING_DKGROUP pivotNextId %s ", str(pivotNextId))
        _logger.info("WARNING_DKGROUP domains %s ", str(domains))"""

        row_values_set = self._get_row_group_values(row_group_bys, search_params)
        col_values_set = self._get_col_group_values(col_group_bys, fields, domains)

        styles = {
            "1": {"bold": True, "fillColor": "#f2f2f2"},
            "2": {"fillColor": "#f2f2f2", "textColor": "#756f6f"},
            "3": {"bold": False, "italic": False, "underline": False, "textColor": "#000000", "fillColor": "#ffffff"},
            "4": {"textColor": "#d00000", "bold": True},
            "5": {"textColor": "#1c9c50", "bold": True},
        }

        conditional_formats = [
            {
                "id": "negative-variation",
                "rule": {
                    "type": "CellIsRule",
                    "operator": "LessThan",
                    "values": ["0"],
                    "style": {"textColor": "#FF0000", "fillColor": ""}
                },
                "ranges": []
            },
            {
                "id": "positive-variation",
                "rule": {
                    "type": "CellIsRule",
                    "operator": "GreaterThan",
                    "values": ["0"],
                    "style": {"textColor": "#6AA84F", "fillColor": ""}
                },
                "ranges": []
            }
        ]

        column_map = {}
        cells = {}
        row_start = 3
        row_index = row_start
        col_offset = 1
        col_state_width = 3

        for i, col_item in enumerate(col_values_set):
            col = col_offset + i * col_state_width
            column_map[col_item["id"]] = col
            cells[f"{self._column_letter(col)}1"] = {"content": col_item["label"], "style": 1}

        total_col = col_offset + len(col_values_set) * col_state_width
        cells[f"{self._column_letter(total_col)}1"] = {"content": "Total", "style": 1}

        for col_item in col_values_set:
            col = column_map[col_item["id"]]
            cells[f"{self._column_letter(col)}2"] = {"content": periods[0], "style": 2}
            cells[f"{self._column_letter(col + 1)}2"] = {"content": periods[1], "style": 2}
            cells[f"{self._column_letter(col + 2)}2"] = {"content": "Variation", "style": 2}

        cells[f"{self._column_letter(total_col)}2"] = {"content": periods[0], "style": 2}
        cells[f"{self._column_letter(total_col + 1)}2"] = {"content": periods[1], "style": 2}
        cells[f"{self._column_letter(total_col + 2)}2"] = {"content": "Variation", "style": 2}

        pivot_mapping = {period: str(i + 1) for i, period in enumerate(periods)}

        for row_value in row_values_set:
            cells[f"A{row_index}"] = {"content": row_value, "style": 2}
            row_values = {}

            for col_item in col_values_set:
                col_val = col_item["id"]
                col = column_map[col_val]
                pivot_id_1 = pivot_mapping.get(periods[0])
                pivot_id_2 = pivot_mapping.get(periods[1])

                c1 = f"{self._column_letter(col)}{row_index}"
                c2 = f"{self._column_letter(col + 1)}{row_index}"
                cv = f"{self._column_letter(col + 2)}{row_index}"

                formula_1 = (
                    f'=IF(ODOO.PIVOT({pivot_id_1},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),'
                    f'ODOO.PIVOT({pivot_id_1},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),0)'
                )
                formula_2 = (
                    f'=IF(ODOO.PIVOT({pivot_id_2},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),'
                    f'ODOO.PIVOT({pivot_id_2},"price_subtotal","{row_group_bys[0]}","{row_value}","{col_group_bys[0]}","{col_val}"),0)'
                )

                cells[c1] = {"content": formula_1, "format": "0.00"}
                cells[c2] = {"content": formula_2, "format": "0.00"}
                cells[cv] = {
                    "content": f"=IF({c1}=0, 0, ROUND(({c2}-{c1})/{c1}*100, 2))",
                    "format": "0.00",
                }

                conditional_formats[0]["ranges"].append(cv)
                conditional_formats[1]["ranges"].append(cv)
                row_values[col_val] = (c1, c2)

            tc1 = f"{self._column_letter(total_col)}{row_index}"
            tc2 = f"{self._column_letter(total_col + 1)}{row_index}"
            tcv = f"{self._column_letter(total_col + 2)}{row_index}"

            cells[tc1] = {"content": f"={'+'.join([v[0] for v in row_values.values()])}", "format": "0.00"}
            cells[tc2] = {"content": f"={'+'.join([v[1] for v in row_values.values()])}", "format": "0.00"}
            cells[tcv] = {
                "content": f"=IF({tc1}=0, 0, ROUND(({tc2}-{tc1})/{tc1}*100, 2))",
                "format": "0.00",
                "style": 3
            }

            conditional_formats[0]["ranges"].append(tcv)
            conditional_formats[1]["ranges"].append(tcv)
            row_index += 1

        cells[f"A{row_index}"] = {"content": "Total", "style": 1}
        for col in range(col_offset, total_col + 3):
            col_letter = self._column_letter(col)
            cells[f"{col_letter}{row_index}"] = {
                "content": f"=ROUND(SUM({col_letter}{row_start}:{col_letter}{row_index - 1}),2)",
                "format": "0.00"
            }

        return {
            "version": 12.5,
            "sheets": [
                {
                    "id": "Sheet1",
                    "name": "Sheet1",
                    "colNumber": total_col + 3,
                    "rowNumber": row_index + 10,
                    "cells": cells,
                    "conditionalFormats": conditional_formats,
                    "merges": [],
                    "figures": [],
                    "filterTables": [],
                    "rows": {},
                    "cols": {},
                    "areGridLinesVisible": True,
                    "isVisible": True,
                }
            ],
            "styles": styles,
            "entities": {},
            "formats": {},
            "borders": {},
            "revisionId": "SPREADSHEET_COMPARAISON_COMPLETE",
            "uniqueFigureIds": True,
            "odooVersion": 5,
            "globalFilters": [],
            "pivots": pivots,
            "pivotNextId": pivotNextId,
            "lists": {},
            "listNextId": 1,
            "chartOdooMenusReferences": {},
        }


    def _insert_pivot_dashboard_spreadsheet(self):
        dashboard = self.env["spreadsheet.dashboard"].create(
            self._create_spreadsheet_dashboard_vals()
        )
        import_data = self.import_data
        import_data["name"] = self.datasource_name
        import_data["new"] = 1
        if self.dynamic:
            import_data["dyn_number_of_rows"] = self.number_of_rows
        if self.dynamic_cols:
            import_data["dyn_number_of_cols"] = self.number_of_cols
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {
                "model": dashboard._name,
                "spreadsheet_id": dashboard.id,
                "import_data": import_data,
            },
        }

    def _insert_pivot_dashboard_spreadsheet(self):
        import_data = self.import_data
        if self._is_comparison_mode():
            # Mode comparaison : création d'un spreadsheet spécial
            spreadsheet_content = self._generate_comparison_spreadsheet_json()
            encoded_data = base64.encodebytes(json.dumps(spreadsheet_content).encode("utf-8"))
            dashboard_vals = self._create_spreadsheet_dashboard_vals()
            dashboard_vals["data"] = encoded_data
            dashboard_vals["name"] = self.datasource_name
            _logger.info("WARNING_DKGROUP customize_dashboard dashboard_vals %s ", str(dashboard_vals))
            spreadsheet = self.env["spreadsheet.dashboard"].create(dashboard_vals)
            return {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_oca",
                "params": {
                    "model": "spreadsheet.dashboard",
                    "spreadsheet_id": spreadsheet.id,
                },
            }
        else:
            dashboard = self.env["spreadsheet.dashboard"].create(
                self._create_spreadsheet_dashboard_vals()
            )
            import_data["name"] = self.datasource_name
            import_data["new"] = 1
            if self.dynamic:
                import_data["dyn_number_of_rows"] = self.number_of_rows
            if self.dynamic_cols:
                import_data["dyn_number_of_cols"] = self.number_of_cols
            return {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_oca",
                "params": {
                    "model": dashboard._name,
                    "spreadsheet_id": dashboard.id,
                    "import_data": import_data,
                },
            }


    def _insert_pivot_new(self):
        import_data = self.import_data
        if self._is_comparison_mode():
            spreadsheet_content = self._generate_comparison_spreadsheet_json()
            #_logger.info("WARNING_DKGROUP customize_dashboard spreadsheet_content %s ", str(spreadsheet_content))
            encoded_data = base64.encodebytes(json.dumps(spreadsheet_content).encode("utf-8"))
            spreadsheet = self.env["spreadsheet.spreadsheet"].create({
                "name": self.datasource_name,
                "data": encoded_data,
            })
            return {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_oca",
                "params": {
                    "model": "spreadsheet.spreadsheet",
                    "spreadsheet_id": spreadsheet.id,
                },
            }

        else:
            import_data["name"] = self.datasource_name
            import_data["new"] = 1
            if self.dynamic:
                import_data["dyn_number_of_rows"] = self.number_of_rows
            if self.dynamic_cols:
                import_data["dyn_number_of_cols"] = self.number_of_cols

            # 3. Création et retour de l'action
            spreadsheet = self.env["spreadsheet.spreadsheet"].create(
                self._create_spreadsheet_vals()
            )

            return {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_oca",
                "params": {
                    "model": spreadsheet._name,
                    "spreadsheet_id": spreadsheet.id,
                    "import_data": import_data,
                },
            }
