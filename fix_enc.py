"""index.html encoding - BOM'suz UTF-8 olarak yeniden kaydet"""
path = r'frontend\index.html'

with open(path, 'rb') as f:
    raw = f.read()

# BOM varsa kaldır
if raw[:3] == b'\xef\xbb\xbf':
    raw = raw[3:]
    print('BOM kaldirildi')

text = raw.decode('utf-8')

fixes = {
    '\u00c3\u00bc': '\u00fc',   # Ã¼ -> ü
    '\u00c3\u2013': '\u00d6',   # Ã– -> Ö
    '\u00c3\u00a7': '\u00e7',   # Ã§ -> ç
    '\u00c4\u00b0': '\u0130',   # Ä° -> İ
    '\u00e2\u20ac\u201c': '\u2014',  # â€" -> —
    '\u00e2\u20ac\u0153': '"',
    '\u00e2\u20ac\u009d': '"',
}
count = 0
for old, new in fixes.items():
    c = text.count(old)
    if c > 0:
        text = text.replace(old, new)
        count += c

print(f'{count} duzeltme yapildi')

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)

with open(path, 'rb') as f:
    r = f.read()
print('BOM:', 'VAR' if r[:3] == b'\xef\xbb\xbf' else 'YOK')
idx = r.find('G\xc3\xbcnl\xc3\xbck'.encode())
print('Gunluk UTF-8:', 'DOGRU' if idx >= 0 else 'HATALI')
