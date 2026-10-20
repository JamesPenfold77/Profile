"""Decode a Profile stored query (.ihq) file - a TQueryByExample saved as a Delphi binary DFM.

Usage:
    python ihq_decode.py <file-or-folder> [...] [--json]

Prints each query's name, description, returned columns (Select), conditions and column
layout, or the same as JSON with --json. Read-only; see SKILL.md for the format.
"""
import glob
import json
import os
import struct
import sys

# ---------------------------------------------------------------- Delphi binary DFM values

def _read_value(b, i):
    """Read one TValueType-tagged value at b[i]. Returns (value, next_index).
    Lists come back as Python lists; identifiers as {'ident': name}."""
    t = b[i]; i += 1
    if t == 0x01:                                   # vaList - values until vaNull
        out = []
        while b[i] != 0x00:
            v, i = _read_value(b, i)
            out.append(v)
        return out, i + 1
    if t == 0x02: return struct.unpack_from('<b', b, i)[0], i + 1        # vaInt8
    if t == 0x03: return struct.unpack_from('<h', b, i)[0], i + 2        # vaInt16
    if t == 0x04: return struct.unpack_from('<i', b, i)[0], i + 4        # vaInt32
    if t == 0x05: return b[i:i + 10].hex(), i + 10                       # vaExtended (raw)
    if t in (0x06, 0x07):                                                 # vaString / vaIdent
        n = b[i]; s = b[i + 1:i + 1 + n].decode('cp1252')
        return (s if t == 0x06 else {'ident': s}), i + 1 + n
    if t == 0x08: return False, i                                        # vaFalse
    if t == 0x09: return True, i                                         # vaTrue
    if t == 0x0A:                                                         # vaBinary
        n = struct.unpack_from('<i', b, i)[0]; return b[i + 4:i + 4 + n].hex(), i + 4 + n
    if t == 0x0C:                                                         # vaLString
        n = struct.unpack_from('<i', b, i)[0]; return b[i + 4:i + 4 + n].decode('cp1252'), i + 4 + n
    if t == 0x0D: return None, i                                         # vaNil
    if t == 0x12:                                                         # vaWString (UTF-16)
        n = struct.unpack_from('<i', b, i)[0]; return b[i + 4:i + 4 + 2 * n].decode('utf-16-le'), i + 4 + 2 * n
    if t == 0x14:                                                         # vaUTF8String
        n = struct.unpack_from('<i', b, i)[0]; return b[i + 4:i + 4 + n].decode('utf-8'), i + 4 + n
    raise ValueError('unhandled DFM value type 0x%02x at offset %d' % (t, i - 1))


def _short(b, i):
    n = b[i]
    return b[i + 1:i + 1 + n].decode('cp1252'), i + 1 + n


def read_object(b):
    """Parse the resource header + TPF0 object. Returns (class_name, {property: value})."""
    tpf = b.find(b'TPF0')
    if tpf < 0:
        raise ValueError('no TPF0 signature - not a Delphi binary DFM')
    i = tpf + 4
    cls, i = _short(b, i)
    _objname, i = _short(b, i)
    props = {}
    while b[i] != 0x00:
        name, i = _short(b, i)
        props[name], i = _read_value(b, i)
    return cls, props

# ---------------------------------------------------------------- TQueryByExample layout

def _chunks(values, size):
    """Select/Conditions are flat lists of fixed-size records, each starting with a version marker."""
    if len(values) % size:
        raise ValueError('list of %d values is not a multiple of %d' % (len(values), size))
    return [values[k:k + size] for k in range(0, len(values), size)]


def _ident(v):
    return v['ident'] if isinstance(v, dict) else v


def decode(path):
    b = open(path, 'rb').read()
    cls, props = read_object(b)
    if cls != 'TQueryByExample':
        raise ValueError('%s: class is %s, expected TQueryByExample' % (path, cls))

    select = []
    for rec in _chunks(props.get('Select', []), 7):
        _ver, field, sort, group, flag, alias, expr = rec
        select.append({'field': field, 'sort': _ident(sort), 'group': _ident(group),
                       'flag': flag, 'alias': alias or '', 'expression': expr or ''})

    conditions, ask = [], 0
    for rec in _chunks(props.get('Conditions', []), 7):
        _ver, field, op, value, connector, flag, extra = rec
        c = {'connector': connector or '', 'field': field, 'op': _ident(op),
             'value': value or '', 'flag': flag, 'extra': extra or ''}
        if c['value'] == '?ask?':
            c['parameter'] = ask             # run-time prompt -> Parameters(ask) from a macro
            ask += 1
        conditions.append(c)

    # Common: [0] version marker '31', [1] int (30 seen), [2] name, [3] description,
    # [4..15] twelve booleans (meaning unknown), [16] category, [17] notes (RTF),
    # [18] result-grid column layout, [19] boolean. Falls back gracefully if shorter.
    common = props.get('Common', [])
    def at(k):
        return common[k] if len(common) > k and isinstance(common[k], str) else ''
    name, description, category, notes_rtf, layout = at(2), at(3), at(16), at(17), at(18)
    columns = []
    if layout:
        # CSV-ish: each entry is  "Title",Alias,Width,Type,Flag,   (Title is itself double-quoted)
        import csv
        for row in csv.reader([layout]):
            for cell in row:
                if cell:
                    parts = next(csv.reader([cell]))
                    if parts and parts[0]:
                        columns.append({'title': parts[0], 'alias': parts[1] if len(parts) > 1 else '',
                                        'width': parts[2] if len(parts) > 2 else ''})
    return {
        'file': os.path.basename(path),
        'name': name,
        'description': description,
        'category': category,
        'notes_rtf': notes_rtf,
        'parameters': ask,
        'select': select,
        'conditions': conditions,
        'columns': columns,
    }

# ---------------------------------------------------------------- output

OPS = {'opEqual': '=', 'opNotEqual': '<>', 'opLess': '<', 'opGreater': '>', 'opEqualLess': '<=',
       'opEqualGreater': '>=', 'opIn': 'IN', 'opNotIn': 'NOT IN', 'opLike': 'LIKE',
       'opIsNull': 'IS NULL', 'opIsNotNull': 'IS NOT NULL'}


def describe(q):
    lines = ['%s  (%s)' % (q['name'], q['file']),
             '  description: %s' % q['description'],
             '  run-time parameters (?ask?): %d' % q['parameters'],
             '  returns (column index: field):']
    for n, s in enumerate(q['select']):
        extra = []
        if s['sort'] not in ('soUnknown', ''): extra.append(s['sort'])
        if s['group'] not in ('gfNone', ''): extra.append(s['group'])
        if s['expression']: extra.append('expr: ' + s['expression'])
        lines.append('    %2d: %s%s' % (n, s['field'], '  [' + ', '.join(extra) + ']' if extra else ''))
    lines.append('  where:')
    for c in q['conditions']:
        val = ('<parameter %d>' % c['parameter']) if 'parameter' in c else c['value']
        lines.append('    %-4s %s %s %s' % (c['connector'].upper(), c['field'], OPS.get(c['op'], c['op']), val))
    return '\n'.join(lines)


def main(argv):
    as_json = '--json' in argv
    paths = []
    for a in (x for x in argv if x != '--json'):
        paths += sorted(glob.glob(os.path.join(a, '*.ihq'))) if os.path.isdir(a) else [a]
    out = [decode(p) for p in paths]
    if as_json:
        print(json.dumps(out, indent=2))
    else:
        print('\n\n'.join(describe(q) for q in out))


if __name__ == '__main__':
    main(sys.argv[1:])
