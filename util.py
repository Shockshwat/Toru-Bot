import discord
import spreadsheet, database
from bot_instance import bot
import asyncio
import logging
from thefuzz import fuzz
logger = logging.getLogger(__name__)


async def get_series_sheet_title(name: str, message) -> str|None:
        logger.info(f'Requesting worksheet title for unknown series: {name}')
        sheets = spreadsheet.get_all_worksheet_titles()
        best_match = None
        best_score = 0
        for s in sheets:
            score = fuzz.token_sort_ratio(name.lower(), s.lower())
            if score > best_score:
                best_score = score
                best_match = s

        suggested = best_match if best_match and best_score >= 70 else None

        class ConfirmView(discord.ui.View):
            def __init__(self, requester_id: int):
                super().__init__(timeout=60)
                self.chosen_title: str | None = None
                self.requester_id = requester_id

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == self.requester_id

            @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
            async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
                if suggested:
                    self.chosen_title = suggested
                await interaction.response.send_message("Using suggested sheet.", ephemeral=True)
                self.stop()

            @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
            async def no(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_message("Please type the correct worksheet title.", ephemeral=True)
                self.stop()

        view = ConfirmView(message.author.id) if suggested else None

        if suggested:
            await message.channel.send(
                f"I don't recognize '{name}'. Did you mean '{suggested}'? Click Yes to confirm, or type the correct worksheet title (case-sensitive).",
                view=view,
            )
        else:
            await message.channel.send(
                f"I don't recognize '{name}'. Please reply with the worksheet title for this series (case-sensitive as in Sheets)."
            )

        def check_msg(m):
            return m.author == message.author and m.channel == message.channel

        chosen_title: str | None = None
        try:
            if view:
                await view.wait()
                if view.chosen_title:
                    chosen_title = view.chosen_title
                    if not spreadsheet.worksheet_exists(chosen_title):
                        logger.warning(f'Suggested worksheet not found: {chosen_title}')
                        await message.channel.send("I couldn't find that worksheet title. Please type the correct one.")
                        chosen_title = None

            if not chosen_title:
                try:
                    reply = await bot.wait_for("message", check=check_msg, timeout=60)
                    sheet_title = reply.content.strip()
                    if not sheet_title:
                        logger.warning(f'Empty title provided by {message.author}')
                        await message.channel.send("Empty title provided. Aborting.")
                        return
                    if not spreadsheet.worksheet_exists(sheet_title):
                        logger.warning(f'Invalid worksheet title provided: {sheet_title}')
                        await message.channel.send("I couldn't find a worksheet with that title. Please check and try again next time.")
                        return
                    chosen_title = sheet_title
                except asyncio.TimeoutError:
                    logger.warning(f'Timeout waiting for worksheet title for {name}')
                    await message.channel.send("Timed out waiting for sheet title.")
                    return

            database.add_series(chosen_title, name)
            logger.info(f'Saved new series alias: {name} -> {chosen_title}')
            await message.channel.send(
                f"Saved alias: '{name}' → worksheet '{chosen_title}'."
            )
            return chosen_title
        except asyncio.TimeoutError:
            logger.warning(f'Timeout waiting for worksheet title for {name}')
            await message.channel.send("Timed out waiting for sheet title.")
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

            class ReplaceView(discord.ui.View):
                def __init__(self, requester_id: int):
                    super().__init__(timeout=30)
                    self.replace = False
                    self.requester_id = requester_id

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user.id == self.requester_id

                @discord.ui.button(label="Replace", style=discord.ButtonStyle.danger)
                async def replace_btn(self, button: discord.ui.Button, interaction: discord.Interaction):
                    self.replace = True
                    await interaction.response.send_message("Replacing entry.", ephemeral=True)
                    self.stop()

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                async def cancel_btn(self, button: discord.ui.Button, interaction: discord.Interaction):
                    await interaction.response.send_message("Cancelled.", ephemeral=True)
                    self.stop()

            view = ReplaceView(message.author.id)
            await message.channel.send(result.get("message"), view=view)
            await view.wait()

            if not view.replace:
                await message.channel.send("No changes made.")
                return

            force_result = spreadsheet.update_task_entry_by_title(
                sheet_title,
                chapter_value,
                task,
                user_name,
                status,
                replace=True,
                replace_col=result.get("replace_col"),
            )
            if not force_result.get("success"):
                logger.error(f'Failed to replace entry: {force_result}')
                await message.channel.send(f"I couldn't update the sheet. {force_result.get('error', 'Please verify the chapter and task.')}")
                return
            logger.info(f'Replaced entry after collision: {sheet_title} ch{chapter_value} {task} -> {user_name} [{status}]')
        else:
            logger.error(f'Failed to update sheet: {sheet_title} ch{chapter_value} {task} - {result.get("error")}')
            await message.channel.send(f"I couldn't update the sheet. {result.get('error', 'Please verify the chapter and task.')}")
            return
    
    logger.info(f'Successfully updated tracker: {sheet_title} ch{chapter_value} {task} -> {user_name} [{status}]')
    await message.channel.send(f"Updated: {sheet_title} • Chapter {chapter_value} • {task} → {user_name} [{status}]")
    return

    
    
