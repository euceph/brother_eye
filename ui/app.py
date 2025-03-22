import asyncio
import logging
import os
import tempfile
from threading import Thread, Event

import speech_recognition as sr
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from services.intents import SimilarityIntentDetector
from services.model import get_ollama_response
from services.stt import listen_to_microphone
from services.time import get_time_data, format_time_data_for_prompt
from services.wake_word import detect_wake_word
from services.weather import get_weather_data, format_weather_data_for_prompt
from ui.widgets import ListeningIndicator, ResponseArea

logger = logging.getLogger(__name__)

class StatusPanel(Static):
    """panel showing current status."""

    def compose(self) -> ComposeResult:
        yield ListeningIndicator(id="listening-indicator", classes="idle")


class AppHeader(Header):
    """custom header for voice assistant."""

    def __init__(self, model="gemma3:4b", wake_word="google"):
        super().__init__()
        self.model = model
        self.wake_word = wake_word

    def render(self) -> str:
        return f"voice assistant | model: {self.model} | wake word: '{self.wake_word}'"


class VoiceAssistantApp(App):
    """main voice assistant app."""

    TITLE = "brother_eye"

    BINDINGS = [
        ("ctrl+w", "toggle_wake_word", "wake word"),
        ("ctrl+l", "toggle_listening", "listen"),
        ("ctrl+s", "stop_all", "stop"),
        ("ctrl+q", "quit", "quit")
    ]

    CSS_PATH = "styles.tcss"

    def __init__(self, model="gemma3:4b", system_prompt=None, wake_word="google"):
        super().__init__()
        self.model = model
        self.system_prompt = system_prompt
        self.wake_word = wake_word.lower()

        self.listening_thread = None
        self.wake_word_thread = None
        self.should_listen = False
        self.detecting_wake_word = False
        self.direct_listening_mode = False
        self.stop_event = Event()
        self.wake_word_detected_event = Event()

        self.temp_dir = None

        try:
            self.brain = SimilarityIntentDetector(model="en_core_web_md")
            logger.info("initialized spacy intent detector")
            self.use_spacy_intent = True
        except Exception as e:
            logger.warning(f"intent detector init failed: {e}")
            self.brain = None
            self.use_spacy_intent = False
            logger.info("falling back to keyword detection")

        try:
            self.ear = sr.Recognizer()
            self.mic_list = sr.Microphone.list_microphone_names()
        except Exception as e:
            print(f"audio init warning: {e}")
            self.ear = sr.Recognizer()

    def compose(self) -> ComposeResult:
        """create child widgets."""
        yield AppHeader(model=self.model, wake_word=self.wake_word)
        with Container(id="app-container"):
            yield StatusPanel(id="status-panel")
            with Container(id="response-container"):
                yield ResponseArea(id="response-area")

        yield Footer()

    def on_mount(self) -> None:
        """handle app mount event."""
        self.theme = "monokai"
        self.query_one("#response-area").update(
            f"[bold]voice assistant ready[/bold]\n\n"
            f"[dim]• press [bold]ctrl+w[/bold] to listen for wake word '[italic]{self.wake_word}[/italic]'[/dim]\n"
            f"[dim]• press [bold]ctrl+l[/bold] to start listening directly[/dim]\n"
            f"[dim]• press [bold]ctrl+s[/bold] to stop listening[/dim]\n"
            f"[dim]• press [bold]ctrl+q[/bold] to quit[/dim]"
        )

    def action_toggle_wake_word(self) -> None:
        """toggle wake word detection."""
        if not self.detecting_wake_word:
            self.start_wake_word_detection()
        else:
            self.stop_all()

    def action_toggle_listening(self) -> None:
        """toggle direct listening."""
        if not self.should_listen:
            self.start_direct_listening()
        else:
            self.stop_all()

    def action_stop_all(self) -> None:
        """stop all listening processes."""
        self.stop_all()

    def action_quit(self) -> None:
        """quit the app."""
        self.should_listen = False
        self.detecting_wake_word = False
        self.direct_listening_mode = False
        self.stop_event.set()
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=1)
        if self.wake_word_thread and self.wake_word_thread.is_alive():
            self.wake_word_thread.join(timeout=1)

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except:
                pass
        self.exit()

    def start_wake_word_detection(self) -> None:
        """start wake word detection."""
        if not self.detecting_wake_word:
            self.detecting_wake_word = True
            self.direct_listening_mode = False
            self.stop_event.clear()
            self.wake_word_detected_event.clear()

            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()

            words_file = os.path.join(self.temp_dir, "keywords.list")
            with open(words_file, "w") as f:
                f.write(f"{self.wake_word} /1e-20/\n")

            self.wake_word_thread = Thread(
                target=detect_wake_word,
                args=(
                    self.wake_word,
                    words_file,
                    self.stop_event,
                    self.detecting_wake_word,
                    self.call_from_thread,
                    self.update_status,
                    self.handle_wake_word_detected,
                    self.auto_stop_listening
                )
            )
            self.wake_word_thread.daemon = True
            self.wake_word_thread.start()

            self.update_status(f"waiting for wake word '{self.wake_word}'...", "wake-word")

    def start_direct_listening(self) -> None:
        """start listening without wake word."""
        if not self.should_listen:
            self.stop_event.clear()
            self.detecting_wake_word = False
            self.direct_listening_mode = True

            self.should_listen = True
            self.listening_thread = Thread(
                target=listen_to_microphone,
                args=(
                    self.ear,
                    self.should_listen,
                    self.stop_event,
                    self.call_from_thread,
                    self.update_status,
                    self.get_ai_response,
                    self.restart_wake_word_detection
                )
            )
            self.listening_thread.daemon = True
            self.listening_thread.start()

            self.update_status("listening for your voice...", "listening")

    def stop_all(self) -> None:
        """stop all listening processes."""
        self.should_listen = False
        self.detecting_wake_word = False
        self.direct_listening_mode = False
        self.stop_event.set()
        status_light = self.query_one(ListeningIndicator)
        status_light.status = "idle"
        status_light.remove_class("listening")
        status_light.remove_class("processing")
        status_light.remove_class("error")
        status_light.remove_class("wake-word")
        status_light.add_class("idle")

    def handle_wake_word_detected(self) -> None:
        """handle wake word by starting speech recognition."""
        if not self.should_listen:
            self.should_listen = True
            self.listening_thread = Thread(
                target=listen_to_microphone,
                args=(
                    self.ear,
                    self.should_listen,
                    self.stop_event,
                    self.call_from_thread,
                    self.update_status,
                    self.get_ai_response,
                    self.restart_wake_word_detection
                )
            )
            self.listening_thread.daemon = True
            self.listening_thread.start()

    def restart_wake_word_detection(self) -> None:
        """restart wake word detection after command."""
        self.should_listen = False

        if self.direct_listening_mode:
            self.direct_listening_mode = False
            status_light = self.query_one(ListeningIndicator)
            status_light.status = "idle"
            status_light.remove_class("listening")
            status_light.remove_class("processing")
            status_light.remove_class("error")
            status_light.remove_class("wake-word")
            status_light.add_class("idle")

        elif self.detecting_wake_word and not self.stop_event.is_set():
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()

            words_file = os.path.join(self.temp_dir, "keywords.list")
            with open(words_file, "w") as f:
                f.write(f"{self.wake_word} /1e-20/\n")

            self.wake_word_thread = Thread(
                target=detect_wake_word,
                args=(
                    self.wake_word,
                    words_file,
                    self.stop_event,
                    self.detecting_wake_word,
                    self.call_from_thread,
                    self.update_status,
                    self.handle_wake_word_detected,
                    self.auto_stop_listening
                )
            )
            self.wake_word_thread.daemon = True
            self.wake_word_thread.start()

        else:
            status_light = self.query_one(ListeningIndicator)
            status_light.status = "idle"
            status_light.remove_class("listening")
            status_light.remove_class("processing")
            status_light.remove_class("error")
            status_light.remove_class("wake-word")
            status_light.add_class("idle")

    def auto_stop_listening(self) -> None:
        """auto stop and return to wake word detection."""
        self.should_listen = False
        self.detecting_wake_word = False
        self.direct_listening_mode = False

    def update_status(self, status: str, class_name: str) -> None:
        """update status indicator.

        args:
            status: status text
            class_name: css class to apply
        """
        status_light = self.query_one(ListeningIndicator)
        status_light.status = status

        status_light.remove_class("listening")
        status_light.remove_class("processing")
        status_light.remove_class("error")
        status_light.remove_class("idle")
        status_light.remove_class("wake-word")

        status_light.add_class(class_name)

    @work
    async def get_ai_response(self, text: str) -> None:
        """get response from ai and display with typing effect.

        args:
            text: user query text
        """
        answer_box = self.query_one(ResponseArea)

        if not answer_box.text:
            answer_box.clear()

        await answer_box.type_response(text, is_user=True)
        await asyncio.sleep(0.1)

        self.update_status("getting ai response...", "processing")

        # detect intent using spacy
        intent_result = None
        if self.use_spacy_intent and self.brain:
            intent_result = self.brain.detect_intent(text)
            logger.info(f"detected intent: {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})")

        # handle different intents
        weather_data = None
        brain_food = text

        # handle location setting intent
        if self.use_spacy_intent and intent_result and intent_result['intent'] == 'LOCATION_SETTING':
            success, message = self.brain.handle_location_setting(text)
            if success:
                brain_food = f"{message} {text}"
            else:
                brain_food = f"{message} {text}"

        # handle weather intent
        elif self.use_spacy_intent and intent_result and intent_result['intent'] == 'WEATHER':
            # extract location from entities
            place = intent_result['entities'].get('location')

            # get weather data
            self.update_status("fetching weather data...", "processing")
            weather_data = await get_weather_data(place)

            if weather_data:
                # format for prompt
                sky_info = format_weather_data_for_prompt(weather_data)

                # add weather data to prompt
                brain_food = f"{text}\n\n{sky_info}"

        # check for time intent
        elif self.use_spacy_intent and intent_result and intent_result['intent'] == 'TIME':
            clock_data = get_time_data()
            time_info = format_time_data_for_prompt(clock_data)
            brain_food = f"{text}\n\n{time_info}"

        try:
            # use augmented text
            brain_stream = get_ollama_response(brain_food, model=self.model, system_prompt=self.system_prompt)

            answer_box.text += "\n\n[bold cyan]brother_eye:[/] "
            answer_box.update(answer_box.text)
            await asyncio.sleep(0.05)

            full_response = ""
            buffer_size = 1024
            for thought in brain_stream:
                if self.stop_event.is_set():
                    break

                full_response += thought
                if len(full_response) > buffer_size:
                    full_response = full_response[-buffer_size:]

                answer_box.text = answer_box.text.rsplit("[bold cyan]brother_eye:[/] ", 1)[0] + \
                                  "[bold cyan]brother_eye:[/] " + full_response
                answer_box.update(answer_box.text)
                await asyncio.sleep(0.01)

            self.restart_wake_word_detection()
        except Exception as e:
            self.update_status(f"error getting response: {str(e)}", "error")
            await answer_box.type_response(f"error: {str(e)}")
            self.restart_wake_word_detection()