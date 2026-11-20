"""
Notes Agent (Specialist Agent)
Responsible for saving personal notes, semantic search, listing, and deletions.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.config import get_settings
from app.agents.tools import (
    note_save,
    note_list,
    note_search,
    note_delete,
    set_reminder,
    list_reminders,
)

settings = get_settings()

NOTES_AGENT_INSTRUCTION = """
You are the Notes Specialist Agent for Synaptix Personal Productivity Assistant.
Your sole responsibility is capturing, searching, and managing the user's personal notes, ideas, and meeting summaries.

CORE RESPONSIBILITIES:
1. Save notes with user content, optional titles, and relevant tags.
2. List recent notes in clear, numbered format.
3. Search existing notes using keywords or semantic concepts.
4. Delete notes when explicitly requested.
5. Schedule linked smart reminders for notes when requested (e.g. "save a note and remind me in 10 minutes").

RULES:
- Always call the provided tools to query or mutate notes.
- When reminders are requested, use set_reminder with delay_minutes for relative times (e.g. delay_minutes=10) and echo the tool's formatted time.
- When saving notes, preserve the user's exact wording and extract helpful tags.
- When searching, return concise summaries highlighting matching content.
- Be brief, organized, and helpful.
"""

notes_agent = LlmAgent(
    name="NotesAgent",
    model=settings.GEMINI_MODEL,
    description="Specialist agent for saving, searching, organizing, and retrieving personal and meeting notes.",
    instruction=NOTES_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=note_save),
        FunctionTool(func=note_list),
        FunctionTool(func=note_search),
        FunctionTool(func=note_delete),
        FunctionTool(func=set_reminder),
        FunctionTool(func=list_reminders),
    ],
)
