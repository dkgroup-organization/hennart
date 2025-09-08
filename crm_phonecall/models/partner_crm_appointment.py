# -*- coding: utf-8 -*-
from odoo import api, fields, models
import pytz
import datetime

class PartnerCrmAppointment(models.Model):
    _name = "partner.crm.appointment"
    _description = "Partner Appointment"

    # --- tes champs existants (inchangés) ---
    type1 = fields.Selection([
        ('spontaneous', 'Spontaneous'),
        ('todo', 'To call'),
    ], string='Type', default='todo')

    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Day', required=True)

    frequency = fields.Selection([
        ('7',  'Every week'),
        ('14', 'Every 2 week'),
        ('21', 'Every 3 week'),
        ('28', 'Every 4 week'),
        ('42', 'Every 6 week'),
    ], string='Frequency', default='7', required=True)

    time = fields.Float(string='Time', default=8.0)

    channel = fields.Selection([
        ('phone', 'Phone'),
        ('fax',   'Fax'),
        ('mail',  'Mail'),
        ('other', 'Other'),
    ], string='Channel', default='phone')

    partner_id = fields.Many2one('res.partner', 'Customer')
    contact_id = fields.Many2one('res.partner', 'Contact')

    # ================= Helpers =================

    @api.model
    def _partner_tz(self, partner):
        """Fuseau prioritaire: partner.tz, sinon tz du contexte, sinon Europe/Paris."""
        tzname = partner.tz or self.env.context.get('tz') or 'Europe/Paris'
        try:
            return pytz.timezone(tzname)
        except Exception:
            return pytz.timezone('Europe/Paris')

    @api.model
    def _float_time_to_hm(self, time_float):
        time_float = time_float or 8.0
        hour = int(time_float)
        minute = int(round((float(time_float) - float(hour)) * 60.0))
        return hour, minute

    @api.model
    def _to_utc_naive(self, dt_localized):
        """Prend un datetime timezone-aware et retourne un naive UTC (pour stockage DB)."""
        return dt_localized.astimezone(pytz.utc).replace(tzinfo=None)

    def _iter_weekly_slots(self, start_dt, end_dt, weekday, time_float, tz):
        """
        Génère toutes les dates UTC (naive) pour un weekday donné (0=lundi..6=dimanche)
        à 'time_float' (heure locale dans 'tz'), dans la fenêtre [start_dt, end_dt].
        """
        start_dt = start_dt.replace(second=0, microsecond=0)
        end_dt = end_dt.replace(second=0, microsecond=0)

        offset = (weekday - start_dt.weekday()) % 7
        first = (start_dt + datetime.timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)

        hour, minute = self._float_time_to_hm(time_float)
        if not (8 <= hour < 20):  # borne simple business
            hour, minute = 8, 0

        cur = first
        while cur <= end_dt:
            local = tz.localize(cur.replace(hour=hour, minute=minute, second=0, microsecond=0), is_dst=None)
            yield self._to_utc_naive(local)
            cur += datetime.timedelta(days=7)

    # ================= Logique "mois glissant" =================

    def create_month_appointments(self, days=31):
        """
        Pour chaque appointment, s’assure que TOUTES les occurrences attendues existent
        entre maintenant et maintenant+days, selon 'day' + 'frequency' (7/14/21/28/42).
        Idempotent : ne crée pas de doublons si ça existe déjà.
        """
        Phone = self.env['crm.phonecall']
        now = fields.Datetime.now()
        window_end = now + datetime.timedelta(days=days)

        for appt in self:
            partner = appt.partner_id
            if not partner:
                continue

            tz = self._partner_tz(partner)
            weekday = int(appt.day)  # '0'..'6'
            freq_days = int(appt.frequency or '7')  # '7','14','21','28','42' -> int
            weekly = list(self._iter_weekly_slots(now, window_end, weekday, appt.time, tz))
            if not weekly:
                continue

            step_weeks = max(1, freq_days // 7)  # 1,2,3,4,6
            desired_dates = [dt for idx, dt in enumerate(weekly) if idx % step_weeks == 0]

            # Récupère ce qui existe déjà dans la fenêtre pour CET appointment (actif)
            existing = Phone.search([
                ('appointment_id', '=', appt.id),
                ('date', '>=', now),
                ('date', '<=', window_end),
                ('state', 'not in', ['cancel', 'done']),
            ])

            # index par minute (tolérance) pour éviter les doublons
            def key_min(dt): return dt.replace(second=0, microsecond=0)
            existing_map = {key_min(x.date): x for x in existing}

            for dt_utc in desired_dates:
                k = key_min(dt_utc)
                if k in existing_map:
                    continue  # déjà planifié (± à la minute)

                Phone.create({
                    'user_id': partner.user_id.id or False,
                    'name': partner.name or '?',
                    'partner_id': partner.id,
                    'partner_phone': partner.phone or '',
                    'partner_mobile': partner.mobile or '',
                    'duration': 0.5,  # 30 min
                    'appointment_id': appt.id,
                    'channel': appt.channel,
                    'type1': appt.type1,
                    'date': dt_utc,
                    'state': 'open',
                })
        return True

    # ================= Hooks & Cron =================

    @api.depends('frequency', 'day', 'contact_id', 'time')
    def init_appointment(self):
        """
        Quand on change la config, on supprime UNIQUEMENT les appels futurs
        liés à CET appointment, puis on remplit le mois à venir.
        """
        now = fields.Datetime.now()
        Phone = self.env['crm.phonecall']
        for appt in self:
            # nettoyer seulement ce qui est à venir pour cet appointment
            Phone.search([
                ('appointment_id', '=', appt.id),
                ('date', '>=', now),
            ]).unlink()
        self.create_month_appointments(days=31)

    def create_next_appointment(self):
        """
        (legacy) Conservée pour compatibilité éventuelle, mais on bascule
        vers la génération "mois glissant".
        """
        return self.create_month_appointments(days=31)

    @api.model
    def cron_phone_appointment(self):
        """
        (legacy) Cron historique → redirige vers la version 'mois glissant'
        pour éviter les trous et garantir 1 mois d’occurences.
        """
        return self.cron_phone_appointment_month(days=31)

    @api.model
    def cron_phone_appointment_month(self, days=31):
        """Cron idempotent (toutes les 6 h OK) : remplit le planning du mois prochain."""
        appointments = self.search([])
        appointments.create_month_appointments(days=days)
        # (optionnel) purge douce de très vieux appels : à ajouter si nécessaire.
        return True
