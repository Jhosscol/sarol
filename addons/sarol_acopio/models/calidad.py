from datetime import timedelta

from odoo import api, fields, models


class SarolCalidad(models.Model):
    _name = 'sarol.calidad'
    _description = 'Resultado de análisis de calidad'
    _order = 'fecha desc, id desc'

    fecha = fields.Date(default=fields.Date.context_today, required=True)
    proveedor_id = fields.Many2one('res.partner', string='Proveedor', required=True)
    resultado = fields.Selection(
        [('aceptable', 'Aceptable'), ('baja', 'Baja calidad')],
        default='aceptable', required=True)
    observacion = fields.Char(string='Observación')
    semana_inicio = fields.Date(
        compute='_compute_semana', store=True, string='Semana (lunes)')

    @api.depends('fecha')
    def _compute_semana(self):
        for rec in self:
            rec.semana_inicio = (
                rec.fecha - timedelta(days=rec.fecha.weekday())) if rec.fecha else False
