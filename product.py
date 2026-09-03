# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.tools import grouped_slice


class Package(metaclass=PoolMeta):
    __name__ = 'product.package'

    @classmethod
    def __setup__(cls):
        super(Package, cls).__setup__()
        cls._create_package.append(
            ('sale.line', 'sale_product_package.msg_product_package_null'),
            )

    @classmethod
    def find_packages(cls, records):
        find_packages = super(Package, cls).find_packages(records)
        if find_packages:
            return find_packages

        Line = Pool().get('sale.line')
        for sub_records in grouped_slice(records):
            lines = Line.search([
                    ('product_package', 'in', list(map(int, sub_records))),
                    ],
                limit=1, order=[])
            if lines:
                return lines
        return False


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    default_sale_package = fields.Many2One(
        'product.package', 'Default Sale Package',
        domain=[
            ('template', '=', Eval('id', -1)),
            ],
        states={
            'invisible': ~Eval('salable', False),
            },
        depends=['salable'])

    def get_sale_package(self):
        return self.default_sale_package or self.default_package


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    default_sale_package = fields.Many2One(
        'product.package', 'Default Sale Package',
        domain=[
            ['OR',
                ('template', '=', Eval('template', -1)),
                ('product', '=', Eval('id', -1)),
                ],
            ],
        states={
            'invisible': ~Eval('salable', False),
            },
        depends=['template', 'salable'])

    def get_sale_package(self):
        return self.default_sale_package or self.template.get_sale_package()
