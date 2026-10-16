import csv
import io


def _boundary(data, final):
    n = len(data)
    last = 0
    in_quotes = False
    field_start = True
    i = 0
    while i < n:
        ch = data[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < n and data[i + 1] == '"':
                    i += 2
                    continue
                in_quotes = False
            i += 1
            continue
        if ch == '"' and field_start:
            in_quotes = True
            field_start = False
            i += 1
            continue
        if ch == '\n':
            i += 1
            last = i
            field_start = True
            continue
        field_start = ch == ','
        i += 1
    if final:
        if in_quotes:
            raise ValueError('unterminated quoted record')
        return n
    return last


def decode(pending, header, text, final=False):
    data = pending + text
    cut = _boundary(data, final)
    chunk = data[:cut]
    rest = data[cut:]
    rows = []
    for values in csv.reader(io.StringIO(chunk)):
        if not values:
            continue
        if header is None:
            header = values
        elif len(values) != len(header):
            raise ValueError('invalid field count')
        else:
            rows.append(dict(zip(header, values)))
    return rest, header, rows
