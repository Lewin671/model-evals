def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        key = b['delivery']
        if key in seen:
            continue
        delta = {}
        try:
            for amount in b['amounts']:
                a = b['account']
                delta[a] = delta.get(a, 0) + int(amount)
        except ValueError:
            continue
        seen.add(key)
        for a, v in delta.items():
            balances[a] = balances.get(a, 0) + v
        accepted += 1
    return {'balances': balances, 'accepted': accepted}