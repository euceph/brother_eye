import logging
from threading import Event
from typing import Callable

import speech_recognition as sr

# set up logging
logger = logging.getLogger(__name__)


class WakeWordError(Exception):
    """exception for wake word detection errors."""
    pass


def detect_wake_word(
        wake_word: str,
        keywords_path: str,
        stop_event: Event,
        detecting_wake_word: bool,
        call_from_thread: Callable,
        update_status: Callable[[str, str], None],
        handle_wake_word_detected: Callable[[], None],
        auto_stop_listening: Callable[[], None]
) -> None:
    """listen for wake word using pocketsphinx.

    args:
        wake_word: wake word to listen for
        keywords_path: path to keywords file
        stop_event: signal to stop listening
        detecting_wake_word: active detection flag
        call_from_thread: function for ui thread calls
        update_status: function to update ui status
        handle_wake_word_detected: function for wake word detection
        auto_stop_listening: function to stop listening
    """
    try:
        try:
            import pocketsphinx as ps
            logger.debug("pocketsphinx loaded")
        except ImportError as e:
            logger.error(f"error importing pocketsphinx: {e}")
            call_from_thread(update_status, "error: pocketsphinx not installed", "error")
            call_from_thread(auto_stop_listening)
            return

        config = ps.Config()
        config["lm"] = None
        config["kws"] = keywords_path

        try:
            ear_decoder = ps.Decoder(config)
            logger.debug("decoder initialized")
        except Exception as e:
            logger.error(f"decoder init error: {e}")
            call_from_thread(update_status, f"decoder error: {str(e)}", "error")
            call_from_thread(auto_stop_listening)
            return

        call_from_thread(update_status, f"listening for '{wake_word}'...", "wake-word")

        listener = sr.Recognizer()
        utterance_active = False

        try:
            with sr.Microphone(sample_rate=16000) as ear:
                try:
                    listener.adjust_for_ambient_noise(ear, duration=0.5)
                    logger.debug("adjusted for background noise")
                except Exception as e:
                    logger.warning(f"noise adjustment error: {e}")
                    # continue anyway, not fatal

                try:
                    ear_decoder.start_utt()
                    utterance_active = True
                    logger.debug("decoder started")
                except Exception as e:
                    logger.error(f"error starting decoder: {e}")
                    call_from_thread(update_status, f"decoder start error: {str(e)}", "error")
                    call_from_thread(auto_stop_listening)
                    return

                while not stop_event.is_set() and detecting_wake_word:
                    try:
                        voice_sample = listener.listen(ear, timeout=1, phrase_time_limit=3)

                        try:
                            sound_bytes = voice_sample.get_raw_data()
                            ear_decoder.process_raw(sound_bytes, False, False)
                        except Exception as e:
                            logger.error(f"audio processing error: {e}")
                            continue

                        if ear_decoder.hyp():
                            hypothesis = ear_decoder.hyp()
                            if hypothesis and wake_word.lower() in hypothesis.hypstr.lower():
                                logger.info(f"wake word '{wake_word}' detected!")
                                call_from_thread(update_status, "wake word detected! listening...",
                                                 "listening")

                                if utterance_active:
                                    try:
                                        ear_decoder.end_utt()
                                        utterance_active = False
                                    except Exception as e:
                                        logger.warning(f"ending utterance warning: {e}")

                                call_from_thread(handle_wake_word_detected)
                                break

                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        logger.error(f"wake word detection error: {e}")
                        # continue loop, don't break on random errors

                if utterance_active:
                    try:
                        ear_decoder.end_utt()
                        utterance_active = False
                    except Exception as e:
                        logger.warning(f"utterance cleanup warning: {e}")

        except Exception as e:
            logger.error(f"microphone error: {e}")
            call_from_thread(update_status, f"mic error: {str(e)}", "error")
            call_from_thread(auto_stop_listening)

        if stop_event.is_set():
            logger.info("wake word detection stopped")
            call_from_thread(update_status, "stopped", "idle")

    except Exception as e:
        logger.critical(f"critical wake word error: {e}")
        call_from_thread(update_status, f"wake word error: {str(e)}", "error")
        call_from_thread(auto_stop_listening)