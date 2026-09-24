# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError


class Configuration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'

    package_required = fields.Boolean('Package Required')

    @staticmethod
    def default_package_required():
        return False


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    product_template = fields.Function(fields.Many2One('product.template',
            "Product's template", context={
                'company': Eval('company', -1),
            }, depends=['company']),
        'on_change_with_product_template')
    product_package = fields.Many2One('product.package', 'Package',
        domain=[
            ['OR',
                ('template', '=', Eval('product_template', 0)),
                ('product', '=', Eval('product', 0)),]
            ],
        states={
            'readonly': Eval('sale_state').in_(['cancelled', 'processing', 'done']),
            })
    package_quantity = fields.Function(fields.Integer('Package Quantity',
            states={
                'readonly': Eval('sale_state').in_(['cancelled', 'processing', 'done']),
                }),
        'on_change_with_package_quantity', setter='set_package_quantity')

    @fields.depends('product_package', 'quantity', 'unit', 'product')
    def on_change_with_package_quantity(self, name=None):
        package_quantity = None
        if self.product_package and self.quantity is not None:
            package_unit = self.product_package.unit
            if not package_unit and self.product:
                package_unit = self.product.default_uom
            if self.unit and package_unit:
                Uom = Pool().get('product.uom')
                quantity = Uom.compute_qty(
                    self.unit, self.quantity, package_unit)
                value = (Decimal(str(quantity)) /
                    Decimal(str(self.product_package.quantity)))
                if value == value.to_integral_value():
                    package_quantity = int(value)
        return package_quantity

    @classmethod
    def set_package_quantity(cls, lines, name, value):
        to_write = []
        for line in lines:
            if not line.product_package or value is None:
                continue
            quantity = value * line.product_package.quantity
            if line.unit:
                quantity = round(float(quantity), line.unit.digits)
            to_write.extend(([line], {'quantity': quantity}))
        if to_write:
            cls.write(*to_write)

    @fields.depends('product_package', 'quantity', 'product')
    def pre_validate(self):
        try:
            super(SaleLine, self).pre_validate()
        except AttributeError:
            pass
        Configuration = Pool().get('sale.configuration')
        if (self.type == 'line' and self.product
                and self.sale_state == 'draft'
                and Configuration(1).package_required
                and not self.product_package):
            raise UserError(gettext(
                'sale_product_package.msg_package_required',
                line=self.product.rec_name))
        if (self.product_package
                and Transaction().context.get('validate_package', True)):
            package_quantity = ((self.quantity or 0.0) /
                self.product_package.quantity)
            if float(int(package_quantity)) != package_quantity:
                raise UserError(gettext(
                    'sale_product_package.msg_package_quantity',
                    qty=self.quantity,
                    product=self.product.rec_name,
                    package=self.product_package.rec_name,
                    package_qty=self.product_package.quantity))

    @fields.depends('product', 'product_package')
    def on_change_product(self):
        super(SaleLine, self).on_change_product()
        if not self.product:
            self.product_package = None
        if self.product and not self.product_package:
            self.product_package = self.product.get_sale_package()

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

    @fields.depends('product_package', 'package_quantity', 'quantity', 'unit',
        methods=['on_change_quantity', 'on_change_with_amount',
            'on_change_with_shipping_date'])
    def on_change_package_quantity(self):
        if (self.product_package and self.package_quantity is not None
                and self.unit):
            self.quantity = round((float(self.package_quantity) *
                self.product_package.quantity), self.unit.digits)
            self.on_change_quantity()
            self.amount = self.on_change_with_amount()

    @fields.depends('package_quantity')
    def on_change_with_shipping_date(self, name=None):
        return super().on_change_with_shipping_date(name=name)


class SaleLineStockProductPackage(metaclass=PoolMeta):
    __name__ = 'sale.line'

    def get_move(self, shipment_type):
        move = super().get_move(shipment_type)
        if move:
            move.product_package = self.product_package
        return move


class HandleShipmentException(metaclass=PoolMeta):
    __name__ = 'sale.handle.shipment.exception'

    def transition_handle(self):
        with Transaction().set_context(validate_package=False):
            return super(HandleShipmentException, self).transition_handle()


class HandleInvoiceException(metaclass=PoolMeta):
    __name__ = 'sale.handle.invoice.exception'

    def transition_handle(self):
        with Transaction().set_context(validate_package=False):
            return super(HandleInvoiceException, self).transition_handle()
