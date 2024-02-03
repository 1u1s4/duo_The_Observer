from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent


def on_connect(unique_id: str) -> bool:
    client: TikTokLiveClient = TikTokLiveClient(unique_id=unique_id)
    client.run()
    respuesta = client.room_id
    print(respuesta)

    return bool(respuesta)

if __name__ == '__main__':
    print(on_connect("klg.gt"))