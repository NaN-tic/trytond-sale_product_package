# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['Sale', 'SaleLine',
    'HandleShipmentException', 'HandleInvoiceException', 'ReturnSale']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def _check_product_has_package_required(cls, sales):
        for sale in sales:
            for line in sale.lines:
                if line.type != 'line':
                    continue
                if (line.product and line.product_has_packages
                        and not line.product_package):
                    return False
        return True

    @classmethod
    def confirm(cls, sales):
        if not cls._check_product_has_package_required(sales):
            raise UserError(gettext(
                'sale_product_package.msg_product_has_package_required'))
        super(Sale, cls).confirm(sales)


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    product_has_packages = fields.Function(fields.Boolean(
            'Product Has packages'),
        'on_change_with_product_has_packages')
    product_template = fields.Function(fields.Many2One('product.template',
            "Product's template", context={
                'company': Eval('company'),
            }, depends=['company']),
        'on_change_with_product_template')
    product_package = fields.Many2One('product.package', 'Package',
        domain=[
            ('product', '=', Eval('product_template', 0))
        ],
        states={
            'invisible': ~Eval('product_has_packages', False),
            'readonly': Eval('sale_state').in_(['cancelled', 'processing', 'done']),
            'required': (Eval('product_has_packages', False)
                & ~Eval('sale_state').in_(['draft', 'quotation', 'cancelled'])),
            },
        depends=['sale_state', 'product_template', 'product_has_packages'])
    package_quantity = fields.Integer('Package Quantity',
        states={
            'invisible': ~Eval('product_has_packages', False),
            'readonly': Eval('sale_state').in_(['cancelled', 'processing', 'done']),
            'required': (Eval('product_has_packages', False)
                & ~Eval('sale_state').in_(['draft', 'quotation', 'cancelled'])),
            },
        depends=['sale_state', 'product_has_packages'])

    @fields.depends('product_package', 'quantity', 'product')
    def pre_validate(self):
        try:
            super(SaleLine, self).pre_validate()
        except AttributeError:
            pass
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
            for package in self.product.template.packages:
                if package.is_default:
                    self.product_package = package
                    break

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

    @fields.depends('product_package', 'package_quantity', 'quantity', 'unit',
        methods=['on_change_quantity', 'on_change_with_amount',
            'on_change_with_shipping_date',])
    def on_change_package_quantity(self):
        if self.product_package and self.package_quantity:
            self.quantity = round((float(self.package_quantity) *
                self.product_package.quantity), self.unit.digits)
            self.on_change_quantity()
            self.amount = self.on_change_with_amount()

    @fields.depends('product_package', 'quantity')
    def on_change_quantity(self):
        super(SaleLine, self).on_change_quantity()
        if self.product_package and self.quantity:
            self.package_quantity = int(self.quantity /
                self.product_package.quantity)

    @fields.depends('package_quantity')
    def on_change_with_shipping_date(self, name=None):
        return super().on_change_with_shipping_date(name=name)


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


class ReturnSale(metaclass=PoolMeta):
    __name__ = 'sale.return_sale'

    def do_return_(self, action):
        action, data = super().do_return_(action)

        if data.get('res_id'):
            sales = self.model.browse(data['res_id'])

            for sale in sales:
                for line in sale.lines:
                    if line.type == 'line' and line.package_quantity:
                        line.package_quantity *= -1
                sale.lines = sale.lines  # Force saving
            self.model.save(sales)

        return action, data
