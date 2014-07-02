#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['SaleLine']
__metaclass__ = PoolMeta


class SaleLine:
    __name__ = 'sale.line'

    product_has_packages = fields.Function(fields.Boolean(
            'Product Has packages'),
        'on_change_with_product_has_packages')
    product_package = fields.Many2One('product.package', 'Package',
        domain=[
            ('product', '=', Eval('product', 0))
            ],
        states={
            'invisible': ~Eval('product_has_packages', False),
            'required': Eval('product_has_packages', False),
            },
        depends=['product', 'product_has_packages'])
    package_quantity = fields.Integer('Package Quantity',
        states={
            'invisible': ~Eval('product_has_packages', False),
            'required': Eval('product_has_packages', False),
            },
        depends=['product_has_packages'])

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        cls._error_messages.update({
                'package_quantity': ('The quantity "%s" of product "%s" is '
                    'not a multiple of it\'s package "%s" quantity "%s".'),
                })

    @fields.depends('product_package', 'quantity', 'product_package',
        'product')
    def pre_validate(self):
        if self.product_package:
            package_quantity = self.quantity / self.product_package.quantity
            if float(int(package_quantity)) != package_quantity:
                self.raise_user_error('package_quantity', (self.quantity,
                    self.product.rec_name, self.product_package.rec_name,
                    self.product_package.quantity))

    @fields.depends('product')
    def on_change_with_product_has_packages(self, name=None):
        if self.product and self.product.packages:
            return True
        return False

    @fields.depends('product_package')
    def on_change_product_package(self):
        res = {}
        if not self.product_package:
            res['quantity'] = None
            res['package_quantity'] = None
        return res

    @fields.depends('product_package', 'package_quantity', 'unit_price',
        'type', methods=['quantity', 'delivery_date'])
    def on_change_package_quantity(self):
        res = {}
        if self.product_package and self.package_quantity:
            self.quantity = (float(self.package_quantity) *
                self.product_package.quantity)
            res['quantity'] = self.quantity
            res.update(self.on_change_quantity())
            res['amount'] = self.on_change_with_amount()
            res['delivery_date'] = self.on_change_with_delivery_date()
        return res

    @fields.depends('product_package', 'quantity')
    def on_change_quantity(self):
        res = super(SaleLine, self).on_change_quantity()
        if self.product_package and self.quantity:
            res['package_quantity'] = int(self.quantity /
                self.product_package.quantity)
        return res
