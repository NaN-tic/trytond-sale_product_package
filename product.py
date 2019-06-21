# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.tools import grouped_slice


__all__ = ['Package']


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
