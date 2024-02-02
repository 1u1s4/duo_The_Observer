import os
import time
import asyncio

from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import ConnectEvent


user = os.environ.get("TIKTOK_USER")
client = TikTokLiveClient(user)

time_stamp = time.strftime("%d-%m-%Y_%H-%M", time.localtime())

@client.on("connect")
async def on_connect(_: ConnectEvent):
    """
    Download the livestream video from TikTok directly!

    """

    client.download(
        path=f"lives/{user}_{time_stamp}_stream.avi",  # File path to save the download to
        duration=None,  # Download FOREVER. Set to any integer above 1 to download for X seconds
        quality="uhd"  # Select video quality. In this case, Ultra-High Definition
    )

    # Stop downloading after 10 seconds.
    await asyncio.sleep(2)
    client.stop_download()


if __name__ == '__main__':
    """
    Note: "ffmpeg" MUST be installed on your machine to run this program
    
    """

    # Run the client and block the main thread
    # await client.start() to run non-blocking
    client.run()