"""Draw an approximate PNG preview of a CDO form (.jfa) without Profile.

Usage:  python -I jfa_preview.py <form.jfa> [out.png] [--scale 2]

Reads the 100502 form-definition row, decodes the embedded DFM and draws the
first page's controls: shapes (incl. stRoundRect), labels (Segoe UI /
Semibold / MDL2 glyphs, colours, underline), edits/memos (border unless
bsNone), radio buttons and checkboxes. Edits show their control name as
placeholder text, never real data.

It is a layout aid only - it does not reproduce VCL exactly (text baselines,
lookup/date buttons, themes). Always confirm in the real CDO designer.
Needs Pillow and the Windows Segoe fonts.
"""
import re
import sys
from PIL import Image, ImageDraw, ImageFont

BS = chr(92)
CRLF = '\r\n'
FONTS = 'C:/Windows/Fonts/'
FONT_FILES = {'Segoe UI': 'segoeui.ttf', 'Segoe UI Semibold': 'seguisb.ttf',
              'Segoe MDL2 Assets': 'segmdl2.ttf'}


def jaffa_decode(v):
    return re.sub(re.escape(BS) + r'([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), v)


def read_dfm(path):
    text = open(path, encoding='utf-8-sig', newline='').read()
    for line in text.split(CRLF):
        f = line.split('\t')
        if len(f) > 13 and f[0] == 'OBSV' and f[2] == '100502':
            return jaffa_decode(f[13])
    raise SystemExit('no 100502 form-definition row found')


def colour(v, default):
    named = {'clWhite': (255, 255, 255), 'clGray': (128, 128, 128), 'clBlack': (0, 0, 0),
             'clBlue': (0, 0, 255), 'clWindowText': (0, 0, 0)}
    if v is None:
        return default
    if v in named:
        return named[v]
    if v.startswith('$'):                      # Delphi $00BBGGRR
        x = int(v[1:], 16)
        return (x & 255, (x >> 8) & 255, (x >> 16) & 255)
    if v.isdigit():
        x = int(v)
        return (x & 255, (x >> 8) & 255, (x >> 16) & 255)
    return default


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    scale = 2
    if '--scale' in sys.argv:
        scale = int(sys.argv[sys.argv.index('--scale') + 1])
        args = [a for a in args if a != str(scale)]
    src = args[0]
    out = args[1] if len(args) > 1 else src.rsplit('.', 1)[0] + ' preview.png'
    d = read_dfm(src)
    S = scale
    root_font = (re.search(r"^  Font\.Name = '(.+?)'", d, re.M) or [None, 'MS Sans Serif'])[1]
    W = int(re.search(r'^  ClientWidth = (\d+)', d, re.M).group(1))
    H = int(re.search(r'^  ClientHeight = (\d+)', d, re.M).group(1))
    page_col = colour((re.search(r'object Page_1: TICDOPanel.*?^\s+Color = (\S+)', d, re.M | re.S)
                       or [None, None])[1], (240, 240, 240))
    img = Image.new('RGB', (W * S, H * S), page_col)
    dr = ImageDraw.Draw(img)

    def font(name, px):
        return ImageFont.truetype(FONTS + FONT_FILES.get(name, 'segoeui.ttf'), px * S)

    for m in re.finditer(r'^        object (\w+): (\w+)\r\n(.*?)^        end', d, re.M | re.S):
        name, cls, body = m.groups()

        def g(p, dflt=None):
            r = re.search(r'^\s+%s = (.+?)\r?$' % re.escape(p), body, re.M)
            return r.group(1) if r else dflt
        if g('Left') is None:
            continue
        l, t, w, h = [int(g(k, '0')) * S for k in ('Left', 'Top', 'Width', 'Height')]
        fname = (g('Font.Name') or "'%s'" % root_font).strip("'")
        style = g('Font.Style', '') or ''
        if 'fsBold' in style and fname == 'Segoe UI':
            fname = 'Segoe UI Semibold'
        px = abs(int(g('Font.Height', '-12')))
        fcol = colour(g('Font.Color'), (0, 0, 0))
        if cls == 'TICDOShape':
            fill = colour(g('FillColor'), (255, 255, 255))
            border = colour(g('BorderColor'), (0, 0, 0))
            box = [l, t, l + w - 1, t + h - 1]
            if g('Shape') == 'stRoundRect':
                # VCL RoundRect corner ellipse is min(w, h) div 4 wide, so the radius is half that
                dr.rounded_rectangle(box, radius=max(S, min(w, h) // 8), fill=fill, outline=border, width=S)
            else:
                dr.rectangle(box, fill=fill, outline=border)
        elif cls == 'TICDOLabel':
            cap = g('Caption', "''")
            if cap.startswith('#'):
                txt = chr(int(cap[1:]))
            else:
                txt = cap.strip("'").replace("''", "'")
            if g('ParentColor') == 'False' and g('Color'):
                dr.rectangle([l, t, l + w - 1, t + h - 1], fill=colour(g('Color'), page_col))
            dr.text((l, t), txt, font=font(fname, px), fill=fcol)
            if 'fsUnderline' in style:
                tw = dr.textlength(txt, font=font(fname, px))
                dr.line([l, t + px * S + 3, l + tw, t + px * S + 3], fill=fcol, width=S)
        elif cls in ('TICDOEdit', 'TICDOMemo', 'TICDORichEdit', 'TICDOComboBox'):
            bg = colour(g('Color'), (255, 255, 255))
            dr.rectangle([l, t, l + w - 1, t + h - 1], fill=bg)
            if g('BorderStyle') != 'bsNone':
                dr.rectangle([l, t, l + w - 1, t + h - 1], outline=(122, 122, 122), width=S)
            ph, pf = name, font('Segoe UI', 11)
            while ph and dr.textlength(ph, font=pf) > w - 6 * S:
                ph = ph[:-1]
            dr.text((l + 3 * S, t + 2 * S), ph, font=pf, fill=(150, 150, 150))
        elif cls in ('TICDORadioButton', 'TICDOCheckBox'):
            if cls == 'TICDORadioButton':
                dr.ellipse([l, t + 3 * S, l + 13 * S, t + 16 * S], outline=(60, 60, 60), width=S)
            else:
                dr.rectangle([l, t + 3 * S, l + 13 * S, t + 16 * S], outline=(60, 60, 60), width=S)
                if g('Checked') == 'True':
                    dr.text((l + 2 * S, t + 1 * S), chr(0xE73E), font=font('Segoe MDL2 Assets', 11),
                            fill=(0, 0, 0))
            dr.text((l + 18 * S, t + 1 * S), (g('Caption') or "''").strip("'"),
                    font=font(fname, px), fill=fcol)
        elif cls == 'TICDOButton':
            dr.rectangle([l, t, l + w - 1, t + h - 1], fill=(225, 225, 225), outline=(173, 173, 173))
            dr.text((l + 8 * S, t + 3 * S), (g('Caption') or "''").strip("'"),
                    font=font(fname, px), fill=(0, 0, 0))
        else:
            dr.rectangle([l, t, l + w - 1, t + h - 1], outline=(200, 0, 200))
            dr.text((l + 2, t + 2), cls, font=font('Segoe UI', 10), fill=(200, 0, 200))
    img.save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
