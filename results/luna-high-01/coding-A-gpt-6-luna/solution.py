def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        key = b['delivery']
        if key in seen:
            continue
        try:
            total = sum(int(amount) for amount in b['amounts'])
        except ValueError:
            continue
        account = b['account']
        balances[account] = balances.get(account, 0) + total
        seen.add(key)
        accepted += 1
    return {'balances': balances, 'accepted': accepted}