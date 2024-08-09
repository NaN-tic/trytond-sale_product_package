import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.exceptions import UserError
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install sale_product_package
        config = activate_modules('sale_product_package')

        # Create company
        _ = create_company()
        company = get_company()

        # Create sale user
        User = Model.get('res.user')
        Group = Model.get('res.group')
        sale_user = User()
        sale_user.name = 'Sale'
        sale_user.login = 'sale'
        sale_group, = Group.find([('name', '=', 'Sales')])
        sale_user.groups.append(sale_group)
        sale_user.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.save()

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()
        account_category_tax, = account_category.duplicate()
        account_category_tax.supplier_taxes.append(tax)
        account_category_tax.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.list_price = Decimal('10')
        template.cost_price = Decimal('5')
        template.cost_price_method = 'fixed'
        template.account_category = account_category_tax
        package = template.packages.new()
        package.name = 'Box'
        package.quantity = 6
        package2 = template.packages.new()
        package2.name = 'Box 2'
        package2.quantity = 2
        package2.is_default = False
        template.save()
        template.reload()
        package, package2 = template.packages
        product.template = template
        product.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Sale products with package
        config.user = sale_user.id
        Sale = Model.get('sale.sale')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        line = sale.lines.new()
        line.product = product
        line.package_quantity = 2
        self.assertEqual(line.quantity, 12.0)
        self.assertEqual(line.amount, Decimal('120.00'))

        line.quantity = 13

        with self.assertRaises(UserError):
            sale.save()

        line.quantity = 12
        self.assertEqual(line.package_quantity, 2)

        line = sale.lines.new()
        line.type = 'comment'
        line.description = 'Test comment'
        sale.save()
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')

        # Return sale
        return_sale = Wizard('sale.return_sale', [sale])
        return_sale.execute('return_')
        returned_sale, = Sale.find([
            ('state', '=', 'draft'),
        ])
        self.assertEqual(returned_sale.origin, sale)
        self.assertEqual(
            sorted([(x.quantity or 0, x.package_quantity or 0)
                    for x in returned_sale.lines]), [(-12.0, -2), (0, 0)])
