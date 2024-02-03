from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent


def on_connect(unique_id: str) -> bool:
    try:
        client: TikTokLiveClient = TikTokLiveClient(unique_id=unique_id)
        client.run()
        respuesta = client.room_id

        return bool(respuesta)
    except Exception as e:
        print(e)
        return False

if __name__ == '__main__':
    #print(on_connect("klg.gt"))
    print(on_connect("edgar_toledo_g"))