"""
Module for accessing and manipulating spreadsheet data.
"""
import gspread
import logging 

logger = logging.getLogger(__name__)

spreadsheet_id = "1C4nokf-Ip-lFMm6j9Al64kI1m5kOHEfTUBNv25gALlo"
gc = gspread.service_account(filename="credentials.json")
sh = gc.open_by_key(spreadsheet_id)

def worksheet_exists(sheet_title: str) -> bool:
    try:
        result = sh.worksheet(sheet_title) is not None
        logger.debug(f'Worksheet "{sheet_title}" exists: {result}')
        return result
    except gspread.WorksheetNotFound:
        logger.warning(f'Worksheet "{sheet_title}" not found')
        return False

def _find_task_start_col_case_insensitive(labels: list[str], task: str) -> int | None:
    target = str(task).strip().lower()
    for idx, label in enumerate(labels, start=1):
        if str(label).strip().lower() == target:
            return idx
    return None

def get_task_columns_by_title(sheet_title: str, task: str) -> tuple[list[int], int] | None:
    logger.debug(f'Looking for task "{task}" columns in "{sheet_title}"')
    ws = sh.worksheet(sheet_title)
    header_row = ws.row_values(2)
    if not header_row:
        logger.warning(f'No header row found in "{sheet_title}"')
        return None
    start_col = _find_task_start_col_case_insensitive(header_row, task)
    if start_col is None:
        logger.warning(f'Task "{task}" not found in header row of "{sheet_title}"')
        return None
    logger.debug(f'Task "{task}" starts at column {start_col}')
    sub_headers = ws.row_values(3)
    
    next_task_col = None
    for idx in range(start_col, len(header_row)):
        if idx > start_col - 1 and header_row[idx].strip():
            next_task_col = idx + 1
            logger.debug(f'Next task section starts at column {next_task_col}')
            break
    
    if next_task_col is None:
        next_task_col = len(sub_headers) + 1
        logger.debug(f'No next task found, scanning until end of headers')
    
    name_cols = []
    status_col = None
    
    for col_idx in range(start_col, next_task_col):
        if col_idx > len(sub_headers):
            break
        cell_label = sub_headers[col_idx - 1] if len(sub_headers) >= col_idx else ""
        cell_lower = str(cell_label).strip().lower()
        
        if cell_lower == "name" or (not cell_label.strip() and len(name_cols) > 0 and status_col is None):
            name_cols.append(col_idx)
            logger.debug(f'Found name column at {col_idx}: "{cell_label}"')
        elif cell_lower == "status":
            status_col = col_idx
            logger.debug(f'Found status column at {col_idx}')
            break
    
    if not name_cols or status_col is None:
        logger.error(f'Could not find Name/Status columns for task "{task}" in "{sheet_title}". Found name_cols={name_cols}, status_col={status_col}')
        logger.debug(f'Sub-headers from col {start_col} to {next_task_col}: {sub_headers[start_col-1:next_task_col-1]}')
        return None
    
    logger.info(f'Task "{task}" in "{sheet_title}": name_cols={name_cols}, status_col={status_col}')
    return (name_cols, status_col)

def find_row_by_chapter_by_title(sheet_title: str, chapter_value: str | int | float) -> int | None:
    ws = sh.worksheet(sheet_title)
    col_a = ws.col_values(1)
    target = str(chapter_value).strip()
    for idx, val in enumerate(col_a, start=1):
        if str(val).strip() == target:
            return idx
    return None

def update_task_entry_by_title(sheet_title: str, chapter_value: str | int | float, task: str, user_name: str, status: str, replace: bool = False, replace_col: int | None = None) -> dict:
    try:
        ws = sh.worksheet(sheet_title)
    except gspread.WorksheetNotFound:
        logger.error(f'Worksheet "{sheet_title}" not found')
        return {"success": False, "error": "Worksheet not found"}
    row_idx = find_row_by_chapter_by_title(sheet_title, chapter_value)
    if row_idx is None:
        logger.error(f'Chapter {chapter_value} not found in "{sheet_title}"')
        return {"success": False, "error": "Chapter not found"}
    cols = get_task_columns_by_title(sheet_title, task)
    if cols is None:
        logger.error(f'Task "{task}" columns not found in "{sheet_title}"')
        return {"success": False, "error": "Task columns not found"}
    name_cols, status_col = cols
    
    if len(name_cols) == 1:
        target_col = name_cols[0]
        existing_name = ws.cell(row_idx, target_col).value
        if existing_name and str(existing_name).strip():
            if not replace:
                logger.warning(f'Single name column at ch{chapter_value} {task} is occupied by "{existing_name}"')
                return {
                    "success": False,
                    "collision": True,
                    "existing_name": existing_name,
                    "replace_col": target_col,
                    "message": f"This task is already assigned to {existing_name}. Would you like to replace them?"
                }
        ws.update_cell(row_idx, target_col, user_name)
        ws.update_cell(row_idx, status_col, status)
        logger.info(f'Updated "{sheet_title}" ch{chapter_value} {task}: {user_name} [{status}]')
        return {"success": True}
    else:
        target_col = None
        for col in name_cols:
            cell_value = ws.cell(row_idx, col).value
            if not cell_value or not str(cell_value).strip():
                target_col = col
                logger.debug(f'Found empty name slot at column {col}')
                break
        
        if target_col is None:
            occupied_names = []
            for col in name_cols:
                cell_value = ws.cell(row_idx, col).value
                if cell_value and str(cell_value).strip():
                    occupied_names.append(str(cell_value).strip())
            logger.warning(f'All name columns for ch{chapter_value} {task} are occupied: {occupied_names}')
            if not replace:
                return {
                    "success": False,
                    "collision": True,
                    "existing_names": occupied_names,
                    "replace_col": name_cols[0],
                    "message": f"All slots are occupied by: {', '.join(occupied_names)}. Replace the first entry?"
                }
            target_col = replace_col if replace_col is not None else name_cols[0]
        
        ws.update_cell(row_idx, target_col, user_name)
        ws.update_cell(row_idx, status_col, status)
        logger.info(f'Updated "{sheet_title}" ch{chapter_value} {task}: {user_name} [{status}] at column {target_col}')
        return {"success": True, "column": target_col}

def get_all_worksheet_titles() -> list[str]:
    titles = [ws.title for ws in sh.worksheets()]
    logger.debug(f'All worksheet titles: {titles}')
    return titles