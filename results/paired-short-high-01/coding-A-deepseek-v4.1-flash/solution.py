def solve(batches):
    balances = {}
    seen = set()
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
        acct = b['account']
        if acct not in balances:
            balances[acct] = 0
        for amt in amounts:
            balances[acct] += amt
        accepted += 1
    return {'balances': balances, 'accepted': accepted}