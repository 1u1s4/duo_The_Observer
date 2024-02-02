from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent
import os
import logging
import time

# Instantiate the client with the user's username
user = os.environ.get("TIKTOK_USER")
client: TikTokLiveClient = TikTokLiveClient(unique_id=user)

# Set up logging
time_stamp = time.strftime("%d-%m-%Y_%H-%M", time.localtime())
log_file = f"logs/{user}_{time_stamp}.log"
# solo guardar los mensajes que se definan en el nivel de logging
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(message)s")

# Define how you want to handle specific events via decorator
@client.on("connect")
async def on_connect(_: ConnectEvent):
    logging.info(f"Connected to Room ID: {client.room_id}")

# Notice no decorator?
async def on_comment(event: CommentEvent):
    logging.info(f"{event.user.nickname} -> {event.comment}")

# Define handling an event via "callback"
client.add_listener("comment", on_comment)

if __name__ == '__main__':
    # Run the client and block the main thread
    # await client.start() to run non-blocking
    client.run()
