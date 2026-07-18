from collector.auth import WhatsAppAuthenticator
from collector.whatsapp import discover_chats

with WhatsAppAuthenticator() as auth:
    page = auth.get_authenticated_page()

    chats = discover_chats(page)

    print(f"Found {len(chats)} chats")

    for chat in chats[:10]:
        print(chat)