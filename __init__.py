# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .sale import *


def register():
    Pool.register(
        SaleLine,
        module='sale_product_package', type_='model')
    Pool.register(
        HandleShipmentException,
        HandleInvoiceException,
        module='sale_product_package', type_='wizard')
