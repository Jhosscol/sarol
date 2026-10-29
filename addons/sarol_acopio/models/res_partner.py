from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sarol_acopiador_id = fields.Many2one(
        'res.users',
        string='Acopiador asignado',
        domain=[('share', '=', False)],
        help='Acopiador responsable de recoger la leche de este proveedor.',
    )
