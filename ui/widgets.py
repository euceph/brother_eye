import asyncio
from textual.reactive import reactive
from textual.widgets import Static
from textual.binding import Binding


class ListeningIndicator(Static):
    """widget to show voice assistant status."""

    status = reactive("idle")

    def render(self) -> str:
        mood_icons = {
            "idle": "💤",
            "listening": "🎤",
            "processing": "⏳",
            "getting ai response": "🤖",
            "error": "❌",
            "waiting for wake word": "👂",
            "streaming speech": "🔊"
        }

        # get base status (before any colon)
        base_mood = self.status.split("'")[0].strip()

        # default icon
        face = mood_icons.get(base_mood, "🔄")

        # escape rich markup
        clean_status = self.status.replace("[", r"\[").replace("]", r"\]")

        return f"{face} {clean_status}"


class ResponseArea(Static):
    """widget to display ai response with typing effect."""

    BINDINGS = [
        Binding("ctrl+c", "copy_text", "copy", show=False)
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = ""
        self.is_typing = False

    def on_mount(self):
        self.styles.padding = (1, 2)
        self.styles.overflow_y = "auto"
        self.styles.overflow_x = "hidden"

    async def type_response(self, text: str, is_user: bool = False) -> None:
        """show text with typing effect.

        args:
            text: text to display
            is_user: whether text is from user
        """
        self.is_typing = True

        try:
            if is_user:
                # user text with typing animation
                person_tag = "[bold red]user:[/] "
                self.text = person_tag
                self.update(self.text)
                await asyncio.sleep(0.05)

                for letter in text:
                    if not self.is_typing:  # check if interrupted
                        break
                    self.text += letter
                    self.update(self.text)
                    await asyncio.sleep(0.01)

                await asyncio.sleep(0.1)
            else:
                # ai responses
                self.text += "\n\n[bold cyan]brother_eye:[/] "
                self.update(self.text)
                await asyncio.sleep(0.05)

                for letter in text:
                    if not self.is_typing:  # check if interrupted
                        break
                    self.text += letter
                    self.update(self.text)
                    await asyncio.sleep(0.01)
        finally:
            self.is_typing = False

    def update_user_text(self, text: str, is_partial: bool = False) -> None:
        """update text with live transcription.

        args:
            text: transcribed text
            is_partial: if partial transcription
        """
        # first update, add user prefix
        if not self.text or not self.text.startswith("[bold red]user:[/] "):
            self.text = "[bold red]user:[/] " + text
        else:
            # update just user part
            parts = self.text.split("[bold cyan]brother_eye:[/]", 1)
            if len(parts) > 1:
                # keep ai response intact
                person_part = "[bold red]user:[/] " + text
                self.text = person_part + "[bold cyan]brother_eye:[/]" + parts[1]
            else:
                # only user text exists
                self.text = "[bold red]user:[/] " + text

        self.update(self.text)

    def stop_typing(self):
        """stop typing animation."""
        self.is_typing = False

    def clear(self):
        """clear all text."""
        self.text = ""
        self.update("")
        self.is_typing = False

    def action_copy_text(self) -> None:
        """copy content to clipboard."""
        if self.text:
            # strip rich markup for plain text
            plain_words = self.text.replace("[bold red]user:[/] ", "you: ")
            plain_words = plain_words.replace("[bold cyan]brother_eye:[/] ", "assistant: ")
            self.app.copy_to_clipboard(plain_words)
            # notify user
            self.notify("conversation copied to clipboard", timeout=2)