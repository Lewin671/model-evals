def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        key = b['delivery']
        if key in seen:
            continue
        try:
            amounts = [int(a) for a in b['amounts']]
        except ValueError:
            continue
        seen.add(key)
        account = b['account']
        for amount in amounts:
            balances[account] = balances.get(account, 0) + amount
        accepted += 1
    return {'balances': balances, 'accepted': accepted}