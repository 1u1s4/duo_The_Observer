import os
import time
import logging
import asyncio

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

# Función para loguear el conteo de espectadores cada 5 segundos
async def log_viewer_count():
    while True:  # Bucle infinito
        logging.info(f"viewer_count: {client.viewer_count}")
        await asyncio.sleep(5)  # Espera 5 segundos antes de la próxima ejecución

# Define handling an event via "callback"
client.add_listener("comment", on_comment)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(log_viewer_count())  # Programa log_viewer_count para que se ejecute concurrentemente
    loop.run_until_complete(client.start())  # Inicia el cliente de forma asíncrona