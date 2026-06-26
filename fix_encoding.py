"""index.html encoding fix - BOM'suz UTF-8 olarak yeniden kaydet"""
import os

path = r'frontend\index.html'

# Dosyayı UTF-8 BOM'lu olarak oku (BOM'u otomatik kaldır)
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Garble'lanmış karakterleri düzelt
replacements = {
    'Ã¼': 'ü', 'Ã–': 'Ö', 'Ä±': 'ı', 'ÅŸ': 'ş', 'Ã§': 'ç', 'ÄŸ': 'ğ',
    'â€"': '—', 'â€œ': '"', 'â€\u009d': '"',
    'Ä°': 'İ', 'Ã‡': 'Ç', 'Åž': 'Ş', 'Äž': 'Ğ',
}

fixed = content
count = 0
for old, new in replacements.items():
    c = fixed.count(old)
    if c > 0:
        fixed = fixed.replace(old, new)
        count += c
        print(f'Duzeltildi ({c}x): {repr(old)} -> {repr(new)}')

print(f'Toplam {count} duzeltme yapildi.')

# BOM'suz UTF-8 olarak kaydet
with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(fixed)

# Doğrulama
with open(path, 'rb') as f:
    raw = f.read()
print('BOM:', 'VAR' if raw[:3] == b'\xef\xbb\xbf' else 'YOK')
idx = raw.find(b'G\xc3\xbcnl\xc3\xbck')
print('Günlük UTF-8:', 'VAR' if idx >= 0 else 'YOK')
idx2 = raw.find(b'<title>')
chunk = raw[idx2:idx2+80]
print('Title:', chunk.decode('utf-8')[:80])
print('Dosya boyutu:', os.path.getsize(path))
