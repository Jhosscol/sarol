from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SarolPlanilla(models.Model):
    _name = 'sarol.planilla'
    _description = 'Planilla diaria de acopio'
    _order = 'fecha desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    fecha = fields.Date(default=fields.Date.context_today, required=True)
    acopiador_id = fields.Many2one(
        'res.users', string='Acopiador',
        default=lambda self: self.env.user, required=True)
    state = fields.Selection(
        [('borrador', 'Borrador'), ('confirmada', 'Confirmada')],
        default='borrador', required=True, string='Estado')
    linea_ids = fields.One2many('sarol.planilla.linea', 'planilla_id', string='Entregas')
    litros_acopiador = fields.Float(
        compute='_compute_litros', store=True, string='Litros según acopiador')
    litros_planta = fields.Float(string='Litros medidos en planta')
    diferencia = fields.Float(
        compute='_compute_diferencia', store=True,
        string='Diferencia (planta - acopiador)')
    puede_editar_planta = fields.Boolean(compute='_compute_puede_editar_planta')

    _sql_constraints = [
        ('fecha_acopiador_uniq', 'unique(fecha, acopiador_id)',
         'Ya existe una planilla de este acopiador para esa fecha.'),
    ]

    @api.depends('fecha', 'acopiador_id')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.fecha or '', rec.acopiador_id.name or '')

    @api.depends('linea_ids.litros')
    def _compute_litros(self):
        for rec in self:
            rec.litros_acopiador = sum(rec.linea_ids.mapped('litros'))

    @api.depends('litros_acopiador', 'litros_planta')
    def _compute_diferencia(self):
        for rec in self:
            rec.diferencia = (rec.litros_planta - rec.litros_acopiador) if rec.litros_planta else 0.0

    def _compute_puede_editar_planta(self):
        user = self.env.user
        ok = user.has_group('sarol_acopio.group_sarol_planta') or \
            user.has_group('sarol_acopio.group_sarol_admin')
        for rec in self:
            rec.puede_editar_planta = ok

    def action_cargar_proveedores(self):
        Linea = self.env['sarol.planilla.linea']
        for rec in self:
            if rec.state != 'borrador':
                continue
            proveedores = self.env['res.partner'].search(
                [('sarol_acopiador_id', '=', rec.acopiador_id.id)])
            if not proveedores:
                raise UserError(_(
                    'No hay proveedores asignados a %s. Asígnalos en Contactos, '
                    'pestaña "Acopio".') % rec.acopiador_id.name)
            nuevos = proveedores - rec.linea_ids.mapped('proveedor_id')
            Linea.create([{'planilla_id': rec.id, 'proveedor_id': p.id} for p in nuevos])
        return True

    def action_confirmar(self):
        for rec in self:
            if not rec.linea_ids:
                raise UserError(_('La planilla no tiene entregas registradas.'))
            rec.state = 'confirmada'
        return True

    def action_borrador(self):
        self.write({'state': 'borrador'})
        return True


class SarolPlanillaLinea(models.Model):
    _name = 'sarol.planilla.linea'
    _description = 'Entrega de un proveedor en una planilla diaria'
    _order = 'proveedor_id'

    planilla_id = fields.Many2one(
        'sarol.planilla', required=True, ondelete='cascade', string='Planilla')
    proveedor_id = fields.Many2one('res.partner', string='Proveedor', required=True)
    litros = fields.Float(string='Litros entregados')
    observacion = fields.Char(string='Observación')
    fecha = fields.Date(related='planilla_id.fecha', store=True)

    _sql_constraints = [
        ('planilla_proveedor_uniq', 'unique(planilla_id, proveedor_id)',
         'Ese proveedor ya está en la planilla.'),
    ]

    @api.constrains('litros')
    def _check_litros(self):
        for rec in self:
            if rec.litros < 0:
                raise ValidationError(_('Los litros no pueden ser negativos.'))
