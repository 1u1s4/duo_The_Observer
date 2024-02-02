import os
import time
import logging

from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent

# Instantiate the client with the user's username
user = os.environ.get("TIKTOK_USER")
client: TikTokLiveClient = TikTokLiveClient(unique_id=user)

# Set up logging
time_stamp = time.strftime("%d-%m-%Y_%H-%M", time.localtime())
log_file = f"logs/{user}_{time_stamp}.log"
# solo guardar los mensajes que se definan en el nivel de logging
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(message)s")

bolsa_de_user_id = []

# Define how you want to handle specific events via decorator
@client.on("connect")
async def on_connect(_: ConnectEvent):
    logging.info(f"Connected to Room ID: {client.room_id}")

# Notice no decorator?
async def on_comment(event: CommentEvent):
    if event.user.user_id not in bolsa_de_user_id:
        bolsa_de_user_id.append(event.user.user_id)
        logging.info(f"user_data: {event.user.user_id} | {event.user.nickname} | {event.user.unique_id} | {event.user.sec_uid} | {event.user.info.following} | {event.user.info.followers} | {event.user.info.follow_role}")
    logging.info(f"{event.user.user_id} -> {event.comment}")

# Define handling an event via "callback"
client.add_listener("comment", on_comment)

if __name__ == '__main__':
    # Run the client and block the main thread
    # await client.start() to run non-blocking
    client.run()
