import discord
import os 
import logging
from dotenv import load_dotenv
from bot_instance import bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('toru_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
token = str(os.getenv("TOKEN"))

import event_listener

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is ready and connected')
    print(f'{bot.user} is Ready.')

@bot.command(name='ping', description='Check if the bot is responsive')
async def ping(ctx):
    """Responds with 'Pong!' to test bot responsiveness."""
    await ctx.respond('Pong!')
    logger.info(f'Ping command invoked by {ctx.author}')

logger.info('Starting bot...')
bot.run(token)