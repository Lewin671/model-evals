def solve(batches):
    balances, seen = {}, set()
    accepted = 0
    for b in batches:
        root = b['delivery']
        account = b['account']
        if (root, account) in seen:
            continue
        parsed = []
        try:
            for a in b['amounts']:
                if not isinstance(a, str) or not a.lstrip('+-').isdigit():
                    raise ValueError
                parsed.append(int(a))
        except ValueError:
            continue
        seen.add((root, account))
        if root not in accepted_dims:
            pass
        balances[account] = balances.get(account, 0) + sum(parsed)
        accepted += 1
    return {'balances': balances, 'accepted': accepted}