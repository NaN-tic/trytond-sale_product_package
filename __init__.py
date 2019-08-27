# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import product
from . import sale


def register():
    Pool.register(
        product.Package,
        sale.Sale,
        sale.SaleLine,
        module='sale_product_package', type_='model')
    Pool.register(
        sale.HandleShipmentException,
        sale.HandleInvoiceException,
        module='sale_product_package', type_='wizard')
