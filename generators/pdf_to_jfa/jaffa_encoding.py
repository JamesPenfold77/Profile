"""
Jaffa value encoding for JFA OBSV field values.

JFA records are TAB-separated. Profile's TJaffaValueEncoding.Encode escapes
characters that would otherwise break the row format:

  - HT  (0x09, tab) -> "\\09"
  - CR  (0x0D)      -> "\\0d"
  - LF  (0x0A)      -> "\\0a"
  - "\\"            -> "\\5c"
  - all other control chars (< 0x20) -> "\\<two hex digits>"

Commas pass through unchanged (tab is the field separator).
"""

def encode(value: str) -> str:
    """Apply Jaffa value encoding to a string."""
    out = []
    for ch in value:
        c = ord(ch)
        if ch == '\\':
            out.append('\\5c')
        elif ch == '\t':
            out.append('\\09')
        elif ch == '\r':
            out.append('\\0d')
        elif ch == '\n':
            out.append('\\0a')
        elif c < 0x20:
            out.append(f'\\{c:02x}')
        else:
            out.append(ch)
    return ''.join(out)


def decode(value: str) -> str:
    """Reverse Jaffa encoding."""
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == '\\' and i + 2 < len(value):
            try:
                out.append(chr(int(value[i+1:i+3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(ch)
        i += 1
    return ''.join(out)
