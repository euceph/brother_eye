import logging
from typing import Callable, Any
from threading import Event

import speech_recognition as sr

# set up logging
logger = logging.getLogger(__name__)


class SpeechRecognitionError(Exception):
    """exception for speech recognition errors."""
    pass


def listen_to_microphone(
        recognizer: sr.Recognizer,
        should_listen: bool,
        stop_event: Event,
        call_from_thread: Callable,
        update_status: Callable[[str, str], None],
        get_ai_response: Callable[[str], None],
        restart_wake_word_detection: Callable[[], None]
) -> None:
    """listen to microphone in background thread.

    args:
        recognizer: speech recognizer instance
        should_listen: listening flag
        stop_event: signal to stop listening
        call_from_thread: function for ui thread calls
        update_status: function to update ui status
        get_ai_response: function to get ai response
        restart_wake_word_detection: function to restart wake word
    """
    try:
        with sr.Microphone() as ear:
            try:
                recognizer.adjust_for_ambient_noise(ear, duration=0.20)
                logger.debug("adjusted for background noise")
            except Exception as e:
                logger.error(f"error adjusting for noise: {e}")
                call_from_thread(update_status, f"error adjusting for noise: {str(e)}", "error")
                call_from_thread(restart_wake_word_detection)
                return

            if should_listen and not stop_event.is_set():
                try:
                    call_from_thread(update_status, "listening...", "listening")

                    voice_sample = None
                    try:
                        voice_sample = recognizer.listen(ear, timeout=5, phrase_time_limit=15)
                        logger.debug("voice captured")
                    except sr.WaitTimeoutError:
                        logger.info("no speech detected (timeout)")
                        if not stop_event.is_set():
                            call_from_thread(update_status, "no speech detected", "error")
                            call_from_thread(restart_wake_word_detection)
                        return

                    if stop_event.is_set():
                        logger.debug("stop event set, exiting")
                        return

                    if voice_sample:
                        call_from_thread(update_status, "processing speech...", "processing")
                        try:
                            words = recognizer.recognize_google(voice_sample)
                            logger.info(f"recognized: {words}")

                            if stop_event.is_set():
                                return

                            if words:
                                call_from_thread(get_ai_response, words)
                        except sr.UnknownValueError:
                            logger.warning("couldn't understand audio")
                            call_from_thread(update_status, "couldn't understand audio", "error")
                            call_from_thread(restart_wake_word_detection)
                        except sr.RequestError as e:
                            logger.error(f"speech service error: {e}")
                            call_from_thread(update_status, f"speech service error: {e}", "error")
                            call_from_thread(restart_wake_word_detection)
                except Exception as e:
                    logger.error(f"error in speech recognition: {e}")
                    if not stop_event.is_set():
                        call_from_thread(update_status, f"error: {str(e)}", "error")
                        call_from_thread(restart_wake_word_detection)
    except Exception as e:
        logger.critical(f"fatal mic error: {e}")
        call_from_thread(update_status, f"fatal mic error: {str(e)}", "error")
        call_from_thread(restart_wake_word_detection)