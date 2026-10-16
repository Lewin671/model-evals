def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        key = (b['account'], b['delivery'])
        if key in seen:
            continue
        try:
            amounts = [int(amount) for amount in b['amounts']]
        except (ValueError, TypeError):
            continue
        seen.add(key)
        account = b['account']
        balances[account] = balances.get(account, 0) + sum(amounts)
        accepted += 1
    return {'balances': balances, 'accepted': accepted}