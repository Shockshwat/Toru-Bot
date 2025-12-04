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
            r"(?i)^(Done|Working|Help)\s+([A-Za-z]+)\s+ch(\d+(?:\.\d+)?)\s+(.+)$"
        )
        reversed_message = ' '.join(reversed(message.content.split()))
        match = status_pattern.match(reversed_message)
        if match:
            status = match.group(1).capitalize()
            task = match.group(2)
            chapter_number = match.group(3)
            name = ' '.join(reversed(match.group(4).split()))

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
