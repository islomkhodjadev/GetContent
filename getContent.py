import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from dotenv import load_dotenv
from utils import scrape_article_data, add_ai_data

load_dotenv()

from urllib.parse import urlparse

SPECIFIC_DOMAIN = "daryo.uz"

TOKEN = getenv("tg_token")

dp = Dispatcher()

import re


@dp.channel_post()
async def command_start_handler(channel_post: Message) -> None:
    urls = []

    # Process URLs from caption_entities
    if channel_post.caption_entities:
        for entity in channel_post.caption_entities:
            if hasattr(entity, "url") and entity.url:  # Ensure the URL attribute exists
                parsed_url = urlparse(entity.url)
                domain = parsed_url.netloc

                # Check if the domain matches the specific one
                if domain == SPECIFIC_DOMAIN:
                    urls.append(entity.url)

    # Process URLs directly from caption
    if channel_post.caption:
        urls += re.findall(r"https?://\S+", channel_post.caption)

    # Remove duplicates
    urls = list(set(urls))

    for url in urls:
        if url is not None:
            # Extract domain from the URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Check if the domain matches the specific one
            if domain != SPECIFIC_DOMAIN:

                continue  # Skip this URL and move to the next one

            # Proceed if the domain matches
            scraped_data = await scrape_article_data(url)

            if "error" not in scraped_data:
                # title and content + url
                result = await add_ai_data(
                    heading=scraped_data["title"] + f"\n url: {url}",
                    content=scraped_data["content"] + f"\n url: {url}",
                    categories=scraped_data["categories"],
                )


@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
