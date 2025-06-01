from odoo import _, models, fields
from odoo.exceptions import AccessError
import logging
_logger = logging.getLogger(__name__)


class SpreadsheetDashboard(models.Model):
    _inherit = 'spreadsheet.dashboard'
    # ... autres champs déjà existants

    dashboard_group_access_type = fields.Selection(
        related='dashboard_group_id.access_type',
        string="Type de droit",
        store=True,
        readonly=True,
    )

    authorized_user_ids = fields.Many2many(
        'res.users',
        'spreadsheet_dashboard_res_users_rel',  # nom de la table relation
        'dashboard_id',
        'user_id',
        string="Utilisateurs autorisés",
        help="Utilisateurs ayant accès à ce dashboard"
    )

    authorized_team_ids = fields.Many2many(
        'crm.team',
        'spreadsheet_dashboard_crm_team_rel',
        'dashboard_id',
        'team_id',
        string="Équipes autorisées",
        help="Équipes commerciales explicitement autorisées à accéder à ce tableau de bord."
    )


    def read(self, fields=None, load='_classic_read'):
        user = self.env.user

        # Admin technique : accès complet
        if user.has_group('base.group_system'):
            return super().read(fields=fields, load=load)

        all_records = super().read(fields=fields, load=load)
        allowed_records = []

        for rec in all_records:
            dashboard_id = rec.get('id')
            if not dashboard_id:
                continue

            dashboard = self.browse(dashboard_id)
            access_type = dashboard.dashboard_group_access_type

            if access_type == 'user':
                if user.id not in dashboard.authorized_user_ids.ids:
                    _logger.warning(
                        "READ_DENIED: L'utilisateur %s n'est pas autorisé à accéder au dashboard '%s' (type: user)",
                        user.name, dashboard.name
                    )
                    raise AccessError(_(
                        "Vous n'êtes pas autorisé à accéder à ce tableau de bord : %s", dashboard.display_name
                    ))

            elif access_type == 'sales_team':
                user_team_ids = user.crm_team_ids.ids
                if not user_team_ids or not dashboard.authorized_team_ids.filtered(lambda t: t.id in user_team_ids):
                    _logger.warning(
                        "READ_DENIED: L'utilisateur %s n'appartient à aucune équipe autorisée pour le dashboard '%s' (type: sales_team)",
                        user.name, dashboard.name
                    )
                    raise AccessError(_(
                        "Vous n'êtes pas autorisé à accéder à ce tableau de bord : %s", dashboard.display_name
                    ))

            # Si autorisé
            allowed_records.append(rec)

        return allowed_records
