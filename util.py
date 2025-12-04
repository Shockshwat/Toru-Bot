import spreadsheet, database
from bot_instance import bot
import asyncio
import logging

logger = logging.getLogger(__name__)


async def get_series_sheet_title(name: str, message) -> str|None:
        
        logger.info(f'Requesting worksheet title for unknown series: {name}')
        await message.channel.send(
            f"I don't recognize '{name}'. Please reply with the worksheet title for this series (case-sensitive as in Sheets)."
        )

        def check(m):
            return (
                m.author == message.author
                and m.channel == message.channel
            )

        try:
            reply = await bot.wait_for("message", check=check, timeout=60)
            sheet_title = reply.content.strip()
            if not sheet_title:
                logger.warning(f'Empty title provided by {message.author}')
                await message.channel.send("Empty title provided. Aborting.")
                return
            if not spreadsheet.worksheet_exists(sheet_title):
                logger.warning(f'Invalid worksheet title provided: {sheet_title}')
                await message.channel.send("I couldn't find a worksheet with that title. Please check and try again next time.")
                return

            database.add_series(sheet_title, name)
            logger.info(f'Saved new series alias: {name} -> {sheet_title}')
            await message.channel.send(
                f"Saved alias: '{name}' → worksheet '{sheet_title}'."
            )
            return sheet_title
        except asyncio.TimeoutError:
            logger.warning(f'Timeout waiting for worksheet title for {name}')
            await message.channel.send("Timed out waiting for sheet number.")
            return

async def get_user_scanname(name: str, message) -> str|None:
    scanname = database.get_user_scannname(name)
    if not scanname:
        logger.info(f'Requesting scanname for unknown user: {name}')
        await message.channel.send(
            f"I don't have a scanname for '{name}'. Please reply with the scanname to use."
        )

        def check(m):
            return (
                m.author == message.author
                and m.channel == message.channel
            )

        try:
            reply = await bot.wait_for("message", check=check, timeout=60)
            scanname = reply.content.strip()
            if not scanname:
                logger.warning(f'Empty scanname provided by {message.author}')
                await message.channel.send("Empty scanname provided. Aborting.")
                return None

            database.add_user(name, scanname)
            logger.info(f'Saved new user scanname: {name} -> {scanname}')
            await message.channel.send(
                f"Saved scanname for '{name}': '{scanname}'."
            )
        except asyncio.TimeoutError:
            logger.warning(f'Timeout waiting for scanname for {name}')
            await message.channel.send("Timed out waiting for scanname.")
            return None
    return scanname
        
async def update_tracker(data: dict, message):
    """
    Updates the tracker with the provided data.
    If the series name is unknown, ask the user for the sheet number
    and store it using database.add_series().
    """
    logger.info(f'Processing tracker update: {data}')
    sheet_title = database.get_series_by_name(data["Name"]) 
    if sheet_title is None:
        sheet_title = await get_series_sheet_title(data["Name"], message)
        if sheet_title is None:
            logger.error(f'Failed to resolve sheet title for {data["Name"]}')
            return
    user_name = await get_user_scanname(message.author.name, message)
    if user_name is None:
        logger.error(f'Failed to resolve scanname for {data["Name"]}')
        return
    chapter_value = data.get("Chapter Number")
    task = data.get("Task")
    status = data.get("Status")

    result = spreadsheet.update_task_entry_by_title(sheet_title, chapter_value, task, user_name, status)
    
    if not result.get("success"):
        if result.get("collision"):
            logger.warning(f'Name collision detected: {result}')
            await message.channel.send(result.get("message"))
            return
        else:
            logger.error(f'Failed to update sheet: {sheet_title} ch{chapter_value} {task} - {result.get("error")}')
            await message.channel.send(f"I couldn't update the sheet. {result.get('error', 'Please verify the chapter and task.')}")
            return
    
    logger.info(f'Successfully updated tracker: {sheet_title} ch{chapter_value} {task} -> {user_name} [{status}]')
    await message.channel.send(f"Updated: {sheet_title} • Chapter {chapter_value} • {task} → {user_name} [{status}]")
    return
        
        
    

    
    
