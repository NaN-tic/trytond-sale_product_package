# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['SaleLine']


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    product_has_packages = fields.Function(fields.Boolean(
            'Product Has packages'),
        'on_change_with_product_has_packages')
    product_template = fields.Function(fields.Many2One('product.template',
            "Product's template"),
        'on_change_with_product_template')
    product_package = fields.Many2One('product.package', 'Package',
        domain=[
            ('product', '=', Eval('product_template', 0))
        ],
        states={
            'invisible': ~Eval('product_has_packages', False),
            'required': Eval('product_has_packages', False),
            },
        depends=['product_template', 'product_has_packages'])
    package_quantity = fields.Integer('Package Quantity',
        states={
            'invisible': ~Eval('product_has_packages', False),
            'required': Eval('product_has_packages', False),
            },
        depends=['product_has_packages'])

    @fields.depends('product_package', 'quantity', 'product')
    def pre_validate(self):
        if self.product_package:
            package_quantity = self.quantity / self.product_package.quantity
            if float(int(package_quantity)) != package_quantity:
                raise UserError(gettext('sale_product_package.package_quantity',
                    qty=self.quantity,
                    product=self.product.rec_name,
                    package=self.product_package.rec_name,
                    package_qty=self.product_package.quantity))

    @fields.depends('product')
    def on_change_with_product_has_packages(self, name=None):
        if self.product and self.product.template.packages:
            return True
        return False

    @fields.depends('product')
    def on_change_with_product_template(self, name=None):
        if self.product:
            return self.product.template.id
        return None

    @fields.depends('product_package')
    def on_change_product_package(self):
        if not self.product_package:
            self.quantity = None
            self.package_quantity = None

    @fields.depends('product_package', 'package_quantity', 'quantity',
        methods=['on_change_quantity', 'on_change_with_amount',
            'on_change_with_shipping_date',])
    def on_change_package_quantity(self):
        if self.product_package and self.package_quantity:
            self.quantity = (float(self.package_quantity) *
                self.product_package.quantity)
            self.on_change_quantity()
            self.amount = self.on_change_with_amount()
            self.shipping_date = self.on_change_with_shipping_date()

    @fields.depends('product_package', 'quantity')
    def on_change_quantity(self):
        super(SaleLine, self).on_change_quantity()
        if self.product_package and self.quantity:
            self.package_quantity = int(self.quantity /
                self.product_package.quantity)
