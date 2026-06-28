import asyncio
from telethon import TelegramClient

async def main():
    client = TelegramClient('stockpilot_session', 30927507, 'a7b6dbbd62f4f68867d491249c6868c0')
    await client.start()
    me = await client.get_me()
    print(f'OK: {me.first_name}')
    
    try:
        entity = await client.get_entity('@veriterminali')
        print(f'Kanal: {entity.title}')
        async for msg in client.iter_messages(entity, limit=1):
            txt = msg.text[:100] if msg.text else '(medya)'
            print(f'Son mesaj ({msg.date}): {txt}')
    except Exception as e:
        print(f'Kanal hata: {e}')
    await client.disconnect()

asyncio.run(main())
