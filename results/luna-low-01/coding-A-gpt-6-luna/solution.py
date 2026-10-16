def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for batch in batches:
        key = batch['delivery']
        if key in seen:
            continue
        try:
            amounts = [int(value) for value in batch['amounts']]
        except ValueError:
            continue
        seen.add(key)
        account = batch['account']
        balances[account] = balances.get(account, 0) + sum(amounts)
        accepted += 1
    return {'balances': balances, 'accepted': accepted}