import json
import logging
from typing import Iterator, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# set up logging
logger = logging.getLogger(__name__)


class OllamaAPIError(Exception):
    """exception raised for ollama api errors."""
    pass


def get_ollama_response(
        text: str,
        model: str = "gemma3:4b",
        system_prompt: Optional[str] = None
) -> Iterator[str]:
    """get ollama response stream.

    args:
        text: prompt text to send
        model: model name to use
        system_prompt: optional system prompt

    returns:
        iterator yielding response chunks

    raises:
        ollama_api_error: if there's a communication error
        connection_error: if ollama server isn't running
        timeout: if request times out
    """
    url = "http://localhost:11434/api/generate"
    brain_food = {
        "model": model,
        "prompt": text,
        "stream": True
    }

    if system_prompt:
        brain_food["system"] = system_prompt

    try:
        response = requests.post(url, json=brain_food, stream=True, timeout=30)
        response.raise_for_status()

        def brain_stream() -> Iterator[str]:
            for thought in response.iter_lines():
                if thought:
                    chunk = thought.decode('utf-8')
                    try:
                        chunk_data = json.loads(chunk)
                        if 'response' in chunk_data:
                            yield chunk_data['response']
                        elif 'error' in chunk_data:
                            logger.error(f"ollama api error: {chunk_data['error']}")
                            raise OllamaAPIError(f"ollama api error: {chunk_data['error']}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"error parsing json response: {e}")
                        continue

        return brain_stream()
    except Timeout:
        logger.error("timeout connecting to ollama")
        raise OllamaAPIError("timeout connecting to ollama") from None
    except ConnectionError:
        logger.error("failed to connect to ollama. is it running?")
        raise OllamaAPIError("failed to connect to ollama. is it running?") from None
    except RequestException as e:
        logger.error(f"error talking to ollama: {e}")
        raise OllamaAPIError(f"error talking to ollama: {e}") from e