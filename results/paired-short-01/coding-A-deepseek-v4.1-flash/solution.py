def solve(batches):
    balances, seen, accepted = {}, set(), 0
    for b in batches:
        key, account, amounts = b['delivery'], b['account'], b['amounts']
        parsed, valid = [], True
        for a in amounts:
            try:
                parsed.append(int(a))
            except (ValueError, TypeError):
                valid = False
                break
        if not valid or key in seen:
            continue
        seen.add(key)
        balances[account] = balances.get(account, 0) + sum(parsed)
        accepted += 1
    return {'balances': balances, 'accepted': accepted}