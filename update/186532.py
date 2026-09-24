if 'pool' not in globals():
    # Prevent pyflakes warnings when the script is not executed by Tryton.
    pool = None
    transaction = None


Configuration = pool.get('sale.configuration')

with transaction.new_transaction(
        _lock_tables=[Configuration._table]) as write_transaction:
    configuration = Configuration(1)
    configuration.package_required = True
    configuration.save()
    write_transaction.commit()
