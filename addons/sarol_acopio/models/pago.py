from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SarolPago(models.Model):
    _name = 'sarol.pago'
    _description = 'Pago semanal a proveedor'
    _order = 'semana_inicio desc, proveedor_id'

    name = fields.Char(compute='_compute_name', store=True)
    semana_inicio = fields.Date(string='Semana (lunes)', required=True)
    semana_fin = fields.Date(compute='_compute_semana_fin', string='Hasta (domingo)')
    proveedor_id = fields.Many2one('res.partner', string='Proveedor', required=True)
    litros_total = fields.Float(string='Litros de la semana')
    baja_calidad = fields.Boolean(string='Baja calidad en la semana')
    tarifa_aplicada = fields.Float(string='Tarifa aplicada (S/ por litro)')
    monto = fields.Float(compute='_compute_monto', store=True, string='Monto a pagar (S/)')
    state = fields.Selection(
        [('borrador', 'Por revisar'), ('con_orden', 'Con orden de compra')],
        default='borrador', required=True, string='Estado')
    purchase_order_id = fields.Many2one('purchase.order', string='Orden de compra', readonly=True)

    _sql_constraints = [
        ('semana_proveedor_uniq', 'unique(semana_inicio, proveedor_id)',
         'Ya existe un pago de ese proveedor para esa semana.'),
    ]

    @api.depends('semana_inicio', 'proveedor_id')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.semana_inicio or '', rec.proveedor_id.name or '')

    @api.depends('semana_inicio')
    def _compute_semana_fin(self):
        for rec in self:
            rec.semana_fin = (
                rec.semana_inicio + timedelta(days=6)) if rec.semana_inicio else False

    @api.depends('litros_total', 'tarifa_aplicada')
    def _compute_monto(self):
        for rec in self:
            rec.monto = round(rec.litros_total * rec.tarifa_aplicada, 2)

    @api.constrains('semana_inicio')
    def _check_lunes(self):
        for rec in self:
            if rec.semana_inicio and rec.semana_inicio.weekday() != 0:
                raise ValidationError(_('La semana debe empezar un lunes.'))

    def _calcular(self):
        """Suma litros de planillas confirmadas, detecta baja calidad y aplica la tarifa."""
        Linea = self.env['sarol.planilla.linea']
        Calidad = self.env['sarol.calidad']
        Tarifa = self.env['sarol.tarifa']
        for rec in self:
            fin = rec.semana_inicio + timedelta(days=6)
            lineas = Linea.search([
                ('proveedor_id', '=', rec.proveedor_id.id),
                ('fecha', '>=', rec.semana_inicio),
                ('fecha', '<=', fin),
                ('planilla_id.state', '=', 'confirmada'),
            ])
            baja = bool(Calidad.search_count([
                ('proveedor_id', '=', rec.proveedor_id.id),
                ('semana_inicio', '=', rec.semana_inicio),
                ('resultado', '=', 'baja'),
            ]))
            tarifa = Tarifa.search(
                [('fecha_desde', '<=', rec.semana_inicio)], order='fecha_desde desc', limit=1)
            normal = tarifa.tarifa_normal if tarifa else 1.20
            reducida = tarifa.tarifa_reducida if tarifa else 1.00
            rec.write({
                'litros_total': sum(lineas.mapped('litros')),
                'baja_calidad': baja,
                'tarifa_aplicada': reducida if baja else normal,
            })

    def action_recalcular(self):
        self.filtered(lambda r: r.state == 'borrador')._calcular()
        return True

    def action_crear_orden(self):
        producto = self.env['product.product'].search([('name', '=', 'Leche cruda')], limit=1)
        if not producto:
            raise UserError(_('No existe el producto "Leche cruda". Créalo en Inventario.'))
        for rec in self:
            if rec.purchase_order_id:
                continue
            if rec.litros_total <= 0:
                raise UserError(_('%s no tiene litros para pagar.') % rec.display_name)
            orden = self.env['purchase.order'].create({
                'partner_id': rec.proveedor_id.id,
                'date_order': datetime.combine(rec.semana_fin, time(12, 0)),
                'origin': rec.name,
                'order_line': [(0, 0, {
                    'product_id': producto.id,
                    'name': _('Leche cruda, semana del %s al %s') % (rec.semana_inicio, rec.semana_fin),
                    'product_qty': rec.litros_total,
                    'product_uom': (producto.uom_po_id or producto.uom_id).id,
                    'price_unit': rec.tarifa_aplicada,
                })],
            })
            rec.write({'purchase_order_id': orden.id, 'state': 'con_orden'})
        return True
