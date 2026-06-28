"""
StockPilot — Telegram Kurulum Yardımcısı
Telethon için gerekli API bilgilerini alır ve test eder.
"""

import os
import sys

print("=" * 60)
print("  StockPilot — Telegram Derinlik Verisi Kurulumu")
print("=" * 60)
print()

print("1. https://my.telegram.org/apps adresine gidin")
print("2. Telefon numaranızla giriş yapın")
print("3. 'Create new application' seçeneğine tıklayın")
print("4. App title: StockPilot, Platform: Desktop")
print("5. Size verilen api_id ve api_hash'i not edin")
print()

api_id = input("api_id: ").strip()
api_hash = input("api_hash: ").strip()
channel = input("Kanal adı (varsayılan: @veriterminali): ").strip()
channel = channel or "@veriterminali"

print()
print(f"API_ID={api_id}")
print(f"API_HASH={api_hash}")
print(f"CHANNEL={channel}")
print()

print("Test ediliyor...")
os.environ['TG_API_ID'] = api_id
os.environ['TG_API_HASH'] = api_hash
os.environ['TG_CHANNEL'] = channel

import asyncio
from telethon import TelegramClient

async def test():
    client = TelegramClient('test_session', int(api_id), api_hash)
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Bağlandı! Kullanıcı: {me.first_name} (@{me.username})")
        
        # Kanalı test et
        try:
            entity = await client.get_entity(channel)
            print(f"✅ '{channel}' kanalı bulundu!")
        except:
            print(f"⚠️ '{channel}' kanalı bulunamadı, ama dinlemeye devam edecek.")
        
        await client.disconnect()
        
        print()
        print("=" * 60)
        print("  KURULUM TAMAMLANDI!")
        print()
        print("  Aşağıdaki komutları PowerShell'de çalıştırın:")
        print(f'  $env:TG_API_ID="{api_id}"')
        print(f'  $env:TG_API_HASH="{api_hash}"')
        print(f'  $env:TG_CHANNEL="{channel}"')
        print("  python run.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        await client.disconnect()

asyncio.run(test())
