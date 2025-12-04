import discord

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = discord.Bot(intents=intents)
