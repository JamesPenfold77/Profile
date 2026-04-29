"""
Jaffa value encoding for JFA OBSV field values.

Profile's TJaffaValueEncoding.Encode escapes characters that would otherwise
break the comma-separated OBSV row format. From the prior sample analysis:

  - CR  (0x0D)  -> "\\0d"
  - LF  (0x0A)  -> "\\0a"
  - ","          -> "\\2c"
  - "\\"         -> "\\5c"
  - all other control chars (< 0x20) -> "\\<two hex digits>"

The encoding uses a literal backslash followed by two lowercase hex digits.
This is the format we observed in the sample DFM blob inside field [13] of the
form-def (100502) row, where embedded CRLF appeared as the four-character
sequence  \\0d\\0a .
"""

def encode(value: str) -> str:
    """Apply Jaffa value encoding to a string for embedding in an OBSV field."""
    out = []
    for ch in value:
        c = ord(ch)
        if ch == '\\':
            out.append('\\5c')
        elif ch == ',':
            out.append('\\2c')
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
        "Hello, world",
        "line one\r\nline two",
        "back\\slash and , comma",
        "tab\there",
    ]
    for s in samples:
        enc = encode(s)
        dec = decode(enc)
        ok = dec == s
        print(f"{'OK' if ok else 'FAIL'}: {s!r}  ->  {enc!r}  ->  {dec!r}")
