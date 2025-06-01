from odoo import models, api,fields
import logging
_logger = logging.getLogger(__name__)


class SpreadsheetDashboardGroup(models.Model):
    _inherit = 'spreadsheet.dashboard.group'

    access_type = fields.Selection(
        selection=[
            ('group', 'Groupes'),
            ('user', 'Utilisateurs'),
            ('sales_team', 'Équipe commerciale'),
        ],
        string="Type de droit",
        default='group',
        required=True,
    )

    authorized_user_count = fields.Integer(
        string="Nombre d'utilisateurs autorisés",
        compute='_compute_authorized_counts',
        store=False,  # On ne stocke pas car ça dépend des dashboards liés dynamiquement
    )
    authorized_team_count = fields.Integer(
        string="Nombre d'équipes autorisées",
        compute='_compute_authorized_counts',
        store=False,
    )

    @api.depends('dashboard_ids.authorized_user_ids', 'dashboard_ids.authorized_team_ids')
    def _compute_authorized_counts(self):
        for group in self:
            user_ids = set()
            team_ids = set()
            for dashboard in group.dashboard_ids:
                user_ids.update(dashboard.authorized_user_ids.ids)
                team_ids.update(dashboard.authorized_team_ids.ids)
            group.authorized_user_count = len(user_ids)
            group.authorized_team_count = len(team_ids)


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        result = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

        user = self.env.user

        # Admin technique : accès total
        if user.has_group('base.group_system'):
            return result

        filtered_result = []

        _logger.info("WARNING_DKGROUP user.sale_team_id.id %s ", str(user.sale_team_id.id))

        for rec in result:
            group_id = rec['id']
            dashboard_group = self.browse(group_id)
            _logger.info("WARNING_DKGROUP dashboard_group %s ", str(dashboard_group))

            if dashboard_group.access_type == 'group':
                filtered_result.append(rec)
                continue

            dashboard_ids = rec.get('dashboard_ids', [])
            if not dashboard_ids:
                continue  # Aucun dashboard, on passe

            domain_dashboards = [('id', 'in', dashboard_ids)]

            if dashboard_group.access_type == 'user':
                domain_dashboards.append(('authorized_user_ids', 'in', user.id))

            elif dashboard_group.access_type == 'sales_team':
                if user.sale_team_id:
                    domain_dashboards.append(('authorized_team_ids', 'in', user.crm_team_ids.ids))
                else:
                    _logger.info(
                        " DashboardGroup '%s' ignoré car l'utilisateur %s n'a pas de team commerciale",
                        dashboard_group.name, user.name
                    )
                    continue  # Pas de team → aucun droit

            dashboards = self.env['spreadsheet.dashboard'].search(domain_dashboards)
            filtered_dashboard_ids = dashboards.ids

            if filtered_dashboard_ids:
                rec['dashboard_ids'] = filtered_dashboard_ids
                filtered_result.append(rec)
            else:
                _logger.info(
                    "DashboardGroup '%s' retiré car aucun dashboard autorisé pour user %s",
                    rec['name'], user.id
                )

        _logger.info("Résultat filtré final : %s", str(filtered_result))

        return filtered_result


    def read(self, fields=None, load='_classic_read'):
        records = super().read(fields=fields, load=load)
        for rec in records:
            _logger.info("WARNING_DKGROUP SpreadsheetDashboardGroup read %s ", str(rec))
        return records