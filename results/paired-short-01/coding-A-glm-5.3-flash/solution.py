def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        key = b['delivery']
        if key in seen:
            continue
        try:
            amounts = [int(a) for a in b['amounts']]
        except (ValueError, TypeError):
            continue
        seen.add(key)
        acct = b['account']
        balances[acct] = balances.get(acct, 0) + sum(amounts)
        accepted += 1
    return {'balances': balances, 'accepted': accepted}