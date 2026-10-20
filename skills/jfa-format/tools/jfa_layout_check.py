"""Offline layout check for a CDO form (.jfa) built in the "modern" style.

Usage:  python -I jfa_layout_check.py <form.jfa>

Conventions it relies on (see the jfa-format skill, "Optional modern form style"):
  shpSec*   section cards (white rounded TICDOShape)
  shpFrm*   rounded frames drawn behind borderless input boxes
  shpHeader the header bar; shp<Button> + lbl<Button>[Icon] make up a rounded button

Reports, and exits 1 if any are found:
  - a control outside the form's client area
  - a row control (not a shape, header or button part) that touches a card but is not
    inside exactly one card (controls clear of every card, like a footer, are allowed)
  - two non-shape controls that overlap (a button's icon + text pair is allowed)
  - a card drawn after controls that sit on it (z-order is DFM order)
  - a windowed control that crosses a frame other than its own
  - a Controls_("name") or OnMClick macro reference that does not exist

Run it on the old version of a form too, as a negative control: an unstyled
form should report problems, which proves the check can fail.
"""
import re
import sys

BS = chr(92)
CRLF = '\r\n'
WINDOWED = ('TICDOEdit', 'TICDOMemo', 'TICDORichEdit', 'TICDOComboBox', 'TICDOCheckBox',
            'TICDORadioButton', 'TICDOListControl', 'TICDOButton')


def jaffa_decode(v):
    return re.sub(re.escape(BS) + r'([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), v)


def read_dfm(path):
    text = open(path, encoding='utf-8-sig', newline='').read()
    for line in text.split(CRLF):
        f = line.split('\t')
        if len(f) > 13 and f[0] == 'OBSV' and f[2] == '100502':
            return jaffa_decode(f[13])
    raise SystemExit('no 100502 form-definition row found')


def macro_text(d):
    """Concatenate every '...' / #NN token in Macros.Strings (good enough for reference scans)."""
    s = d.index('  Macros.Strings = (')
    e = d.index(CRLF + '  OnM', s) if CRLF + '  OnM' in d[s:] else d.index('  PixelsPerInch', s)
    block = d[s:e]
    out = []
    for m in re.finditer(r"'((?:[^']|'')*)'|#(\d+)", block):
        out.append(m.group(1).replace("''", "'") if m.group(1) is not None else chr(int(m.group(2))))
    return ''.join(out)


def main():
    d = read_dfm(sys.argv[1])
    W = int(re.search(r'^  ClientWidth = (\d+)', d, re.M).group(1))
    H = int(re.search(r'^  ClientHeight = (\d+)', d, re.M).group(1))
    ctrls = []
    for m in re.finditer(r'^        object (\w+): (\w+)\r\n(.*?)^        end', d, re.M | re.S):
        body = m.group(3)

        def g(p):
            r = re.search(r'^\s+%s = (-?\d+)' % p, body, re.M)
            return int(r.group(1)) if r else 0
        ctrls.append((m.group(1), m.group(2), g('Left'), g('Top'), g('Width'), g('Height')))
    names = [c[0] for c in ctrls]
    cards = [c for c in ctrls if c[0].startswith('shpSec')]
    frames = [c for c in ctrls if c[0].startswith('shpFrm')]
    buttons = {c[0][3:] for c in ctrls if c[1] == 'TICDOShape'
               and not c[0].startswith(('shpSec', 'shpFrm', 'shpHeader'))}
    problems = []

    def inside(a, b):
        return a[2] >= b[2] and a[3] >= b[3] and a[2] + a[4] <= b[2] + b[4] and a[3] + a[5] <= b[3] + b[5]

    def overlap(a, b):
        return a[2] < b[2] + b[4] and b[2] < a[2] + a[4] and a[3] < b[3] + b[5] and b[3] < a[3] + a[5]

    def is_button_part(n):
        return any(n in ('lbl' + b, 'lbl' + b + 'Icon') for b in buttons)

    header_parts = [c[0] for c in ctrls if c[0] != 'shpHeader' and any(
        h[0] == 'shpHeader' and inside(c, h) for h in ctrls)]
    for c in ctrls:
        n = c[0]
        if c[2] + c[4] > W or c[3] + c[5] > H or c[2] < 0 or c[3] < 0:
            problems.append('outside form: %s' % (c,))
        if c[1] == 'TICDOShape' or is_button_part(n) or n in header_parts:
            continue
        holders = [k[0] for k in cards if inside(c, k)]
        touching = [k[0] for k in cards if overlap(c, k)]
        # free-standing header/footer items (e.g. the version label) touch no card at all
        if touching and len(holders) != 1:
            problems.append('not inside exactly one card: %s %s' % (c, touching))
        for k in cards:
            if inside(c, k) and names.index(k[0]) > names.index(n):
                problems.append('card %s drawn after %s (move the card earlier)' % (k[0], n))
    solo = [c for c in ctrls if c[1] != 'TICDOShape']
    for i in range(len(solo)):
        for j in range(i + 1, len(solo)):
            a, b = solo[i], solo[j]
            if overlap(a, b):
                pair = {a[0], b[0]}
                if any(pair == {'lbl' + x, 'lbl' + x + 'Icon'} for x in buttons):
                    continue
                problems.append('overlap: %s / %s' % (a, b))
    for c in ctrls:
        if c[1] not in WINDOWED:
            continue
        for f in frames:
            if overlap(c, f) and not inside(c, f):
                problems.append('%s crosses frame %s border' % (c[0], f[0]))
    for f in frames:
        if not any(c[1] in WINDOWED and inside(c, f) for c in ctrls):
            problems.append('frame %s has no input box inside it' % f[0])
    mt = macro_text(d)
    for ref in sorted(set(re.findall(r'[Cc]ontrols_\("(\w+)"\)', mt))):
        if ref not in names and ref not in ('Edit1', 'edtAltContactName'):  # template help text
            problems.append('macro references missing control %s' % ref)
    for mac in set(re.findall(r"OnMClick = '(\w+)'", d)):
        if mac + '=' not in mt:
            problems.append('OnMClick macro %s not in Macros.Strings' % mac)
    for p in problems:
        print('PROBLEM:', p)
    print('%d controls, %d cards, %d frames, %d problems' % (len(ctrls), len(cards), len(frames),
                                                             len(problems)))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
