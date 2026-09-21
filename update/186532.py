if 'pool' not in globals():
    # Prevent pyflakes warnings when the script is not executed by Tryton.
    pool = None
    transaction = None


Configuration = pool.get('sale.configuration')
configuration = Configuration(1)
configuration.package_required = True
configuration.save()

transaction.commit()
