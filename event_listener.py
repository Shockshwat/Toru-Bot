from bot_instance import bot
import re
import logging
from util import update_tracker

logger = logging.getLogger(__name__)


@bot.event
async def on_message(message):
    # if message.channel.id == 1005760529400352788:
        if message.author.bot:
            return

        logger.info(
            f"Processing message from channel {message.channel.id}: {message.content}"
        )
        status_pattern = re.compile(
            r"(?i)^(.+?)\s+ch\s*(\d+(?:\.\d+)?)\s+([A-Za-z]+)\s+(Done|Working|Help)$"
        )
        cleaned = ' '.join(message.content.split())
        match = status_pattern.match(cleaned)
        if match:
            name = match.group(1)
            chapter_number = match.group(2)
            task = match.group(3)
            status = match.group(4).capitalize()

            response = {
                "Name": name,
                "Chapter Number": chapter_number,
                "Task": task,
                "Status": status,
            }
            logger.info(f"Matched status update: {response}")
            await update_tracker(response, message)
        else:
            logger.debug(f"Message did not match pattern: {message.content}")


logger.info("Event listener for on_message has been set up")
