from datetime import timedelta

from odoo import fields, models, _
from odoo.exceptions import UserError


def _lunes_semana_pasada(self):
    hoy = fields.Date.context_today(self)
    return hoy - timedelta(days=hoy.weekday() + 7)


class SarolGenerarPagos(models.TransientModel):
    _name = 'sarol.pago.generar'
    _description = 'Generar pagos semanales'

    semana_inicio = fields.Date(
        string='Cualquier día de la semana', required=True, default=_lunes_semana_pasada)

    def action_generar(self):
        self.ensure_one()
        lunes = self.semana_inicio - timedelta(days=self.semana_inicio.weekday())
        fin = lunes + timedelta(days=6)
        lineas = self.env['sarol.planilla.linea'].search([
            ('fecha', '>=', lunes), ('fecha', '<=', fin),
            ('planilla_id.state', '=', 'confirmada'), ('litros', '>', 0)])
        proveedores = lineas.mapped('proveedor_id')
        if not proveedores:
            raise UserError(_('No hay planillas confirmadas con litros en esa semana.'))
        Pago = self.env['sarol.pago']
        pagos = Pago
        for prov in proveedores:
            pago = Pago.search(
                [('semana_inicio', '=', lunes), ('proveedor_id', '=', prov.id)], limit=1)
            if not pago:
                pago = Pago.create({'semana_inicio': lunes, 'proveedor_id': prov.id})
            if pago.state == 'borrador':
                pago._calcular()
            pagos |= pago
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pagos de la semana'),
            'res_model': 'sarol.pago',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pagos.ids)],
        }
