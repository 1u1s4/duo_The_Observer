from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent

client: TikTokLiveClient = TikTokLiveClient(unique_id="@gashi_137")
print(client.room_id)
