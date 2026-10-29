from odoo import fields, models


class SarolTarifa(models.Model):
    _name = 'sarol.tarifa'
    _description = 'Tarifa por litro'
    _order = 'fecha_desde desc'
    _rec_name = 'fecha_desde'

    fecha_desde = fields.Date(string='Vigente desde', required=True)
    tarifa_normal = fields.Float(string='Tarifa normal (S/ por litro)', default=1.20, required=True)
    tarifa_reducida = fields.Float(
        string='Tarifa por baja calidad (S/ por litro)', default=1.00, required=True)
