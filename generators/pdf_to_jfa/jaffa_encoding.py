"""
Jaffa value encoding for JFA OBSV field values.

JFA records are TAB-separated. Profile's TJaffaValueEncoding.Encode escapes
characters that would otherwise break the row format:

  - HT  (0x09, tab) -> "\\09"   (the field separator — must be escaped in values)
  - CR  (0x0D)      -> "\\0d"
  - LF  (0x0A)      -> "\\0a"
  - "\\"            -> "\\5c"
  - all other control chars (< 0x20) -> "\\<two hex digits>"

Commas are NOT escaped — they pass through unchanged, since tab is the field
separator. This was a discovery during first-import testing: an earlier
version of this module assumed comma-separation (escaping `,` as `\\2c`),
which produced files Profile rejected with "incorrect format".

The encoding uses a literal backslash followed by two lowercase hex digits.
"""

def encode(value: str) -> str:
    """Apply Jaffa value encoding to a string for embedding in an OBSV field."""
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
    """Reverse Jaffa encoding (useful for round-trip testing against samples)."""
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


if __name__ == '__main__':
    samples = [
        "Hello, world",                # commas pass through
        "line one\r\nline two",        # CRLF -> \0d\0a
        "back\\slash and , comma",     # backslash escaped, comma not
        "tab\there",                   # tab -> \09
        "field1\tfield2",              # internal tab in a value
    ]
    for s in samples:
        enc = encode(s)
        dec = decode(enc)
        ok = dec == s
        print(f"{'OK' if ok else 'FAIL'}: {s!r}  ->  {enc!r}  ->  {dec!r}")
