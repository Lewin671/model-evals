def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        account, key = b['account'], b['delivery']
        if (account, key) in seen:
            continue
        try:
            amounts = [int(a) for a in b['amounts']]
        except (ValueError, TypeError):
            continue
        seen.add((account, key))
        balances.setdefault(account, 0)
        for a in amounts:
            balances[account] += a
        accepted += 1
    return {'balances': balances, 'accepted': accepted}