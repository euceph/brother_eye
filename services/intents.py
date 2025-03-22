import json
import logging
import os
from typing import Dict, Any, Tuple, Optional

import spacy

# set up logging
logger = logging.getLogger(__name__)

# location config constants
DEFAULT_LOCATION = "Santa Cruz"
LOCATION_CONFIG_FILE = "location_config.json"


class SimilarityIntentDetector:
    """detects user intent using spacy word vectors."""

    def __init__(self, model="en_core_web_md"):
        """initialize the intent detector.

        args:
            model: spacy model to use (needs word vectors)
        """
        try:
            self.brain = spacy.load(model)
            logger.info(f"loaded spacy model: {model}")
        except Exception as e:
            logger.error(f"error loading spacy model: {e}")
            raise ValueError(f"failed to load spacy model '{model}': {e}")

        # intent categories with examples
        self.intent_examples = {
            "WEATHER": [
                "what's the weather like",
                "how's the weather today",
                "is it going to rain",
                "what's the temperature outside",
                "will it be sunny tomorrow",
                "what's the forecast",
                "how hot is it today",
                "is it cold outside",
                "what's the weather in"
            ],
            "TIME": [
                "what time is it",
                "what's the current time",
                "tell me the time",
                "what's today's date",
                "what day is it",
                "what month is it",
                "what's the date today",
                "tell me today's date",
                "what year is it"
            ],
            "LOCATION_SETTING": [
                "set my location to",
                "change my location to",
                "update my location to",
                "my location is",
                "i'm in",
                "set my location",
                "remember my location",
                "save my location as"
            ]
        }

        # process examples
        self.processed_examples = {}
        for intent, examples in self.intent_examples.items():
            self.processed_examples[intent] = [self.brain(ex) for ex in examples]

        logger.info("initialized intent examples")

    def detect_intent(self, text: str) -> Dict[str, Any]:
        """detect user intent using semantic similarity.

        args:
            text: user input text

        returns:
            dict with detected intent and confidence
        """
        # process input
        doc = self.brain(text.lower())

        # find best match
        best_intent = None
        best_score = 0.0
        best_example = None
        all_scores = {}

        # compare with each category
        for intent, examples in self.processed_examples.items():
            # find best score for this intent
            intent_scores = [doc.similarity(ex) for ex in examples]
            best_intent_score = max(intent_scores)
            best_example_idx = intent_scores.index(best_intent_score)

            all_scores[intent] = best_intent_score

            # track overall best
            if best_intent_score > best_score:
                best_score = best_intent_score
                best_intent = intent
                best_example = self.intent_examples[intent][best_example_idx]

        # require good enough match
        threshold = 0.70  # adjustable
        detected_intent = best_intent if best_score >= threshold else None

        result = {
            "original_text": text,
            "intent": detected_intent,
            "confidence": best_score,
            "all_scores": all_scores,
            "best_matching_example": best_example,
            "entities": self.extract_entities(doc)
        }

        return result

    def extract_entities(self, doc) -> Dict[str, Any]:
        """extract entities from spacy document.

        args:
            doc: spacy document

        returns:
            dict of extracted entities
        """
        found_things = {}

        # extract locations
        places = []
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                places.append(ent.text)

        if places:
            found_things["location"] = places[0]

        # extract date/time
        for ent in doc.ents:
            if ent.label_ == "DATE" or ent.label_ == "TIME":
                found_things["datetime"] = ent.text

        return found_things

    def is_weather_query(self, text: str) -> Tuple[bool, Optional[str]]:
        """check if text is weather-related and extract location.

        args:
            text: user's query

        returns:
            tuple of (is_weather_query, location)
        """
        result = self.detect_intent(text)

        is_weather = result["intent"] == "WEATHER"
        location = result["entities"].get("location")

        return is_weather, location

    def is_time_query(self, text: str) -> bool:
        """check if text is time-related.

        args:
            text: user's query

        returns:
            true if time query, false otherwise
        """
        result = self.detect_intent(text)
        return result["intent"] == "TIME"

    def is_location_setting(self, text: str) -> Tuple[bool, Optional[str]]:
        """check if query is about setting location.

        args:
            text: user's query

        returns:
            tuple of (is_location_setting, location)
        """
        result = self.detect_intent(text)

        is_setting_location = result["intent"] == "LOCATION_SETTING"
        location = result["entities"].get("location")

        return is_setting_location, location

    def extract_location_from_text(self, text: str) -> Optional[str]:
        """extract location from raw text.

        args:
            text: text to extract from

        returns:
            location or none if not found
        """
        # use spacy entity recognition first
        doc = self.brain(text)
        places = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
        if places:
            return places[0]

        # fallback to pattern matching if no entities found
        text_lower = text.lower()
        location_phrases = [
            "set my location to ",
            "change my location to ",
            "update my location to ",
            "my location is ",
            "i'm in ",
            "i am in ",
            "save my location as "
        ]

        for phrase in location_phrases:
            if phrase in text_lower:
                # get location after phrase
                place = text_lower.split(phrase, 1)[1].strip()
                # remove sentence endings
                for ending in ['.', '?', '!']:
                    if ending in place:
                        place = place.split(ending, 1)[0].strip()
                return place if place else None

        return None

    def save_location(self, location: str) -> bool:
        """save user's location preference.

        args:
            location: location to save

        returns:
            true if successful, false otherwise
        """
        try:
            config = {'location': location}
            with open(LOCATION_CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            logger.info(f"saved location: {location}")
            return True
        except Exception as e:
            logger.error(f"error saving location: {e}")
            return False

    def get_saved_location(self) -> str:
        """get user's saved location.

        returns:
            saved location or default
        """
        try:
            if os.path.exists(LOCATION_CONFIG_FILE):
                with open(LOCATION_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get('location', DEFAULT_LOCATION)
        except Exception as e:
            logger.error(f"error reading location config: {e}")

        return DEFAULT_LOCATION

    def handle_location_setting(self, text: str) -> Tuple[bool, str]:
        """handle location setting intent.

        args:
            text: user's query

        returns:
            tuple of (success, response_message)
        """
        # check if it's a location setting query
        is_setting, location = self.is_location_setting(text)

        if not is_setting:
            return False, ""

        # if no location detected by entity recognition, try pattern matching
        if not location:
            location = self.extract_location_from_text(text)

        if location:
            success = self.save_location(location)
            if success:
                return True, f"i've set your location to {location}."
            else:
                return False, f"i had trouble saving your location. please try again."
        else:
            return False, f"i couldn't determine what location you want to set. please try again with a clear location name."


# example usage
def example_usage():
    # create detector with word vectors
    mind_reader = SimilarityIntentDetector()

    # test queries
    test_questions = [
        "What's the weather like in Paris?",
        "What time is it now?",
        "Set my location to Tokyo",
        "Tell me a joke",
        "I want to know if I need an umbrella tomorrow",
        "Is it late in the evening?",
        "My location is Berlin",
        "I'm in New York City",
    ]

    for question in test_questions:
        result = mind_reader.detect_intent(question)
        print(f"Query: {question}")
        print(f"Detected intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Best matching example: '{result['best_matching_example']}'")
        print(f"Entities: {result['entities']}")

        # test location setting
        if result['intent'] == 'LOCATION_SETTING':
            success, message = mind_reader.handle_location_setting(question)
            print(f"Location setting: {message}")
            if success:
                saved = mind_reader.get_saved_location()
                print(f"Saved location: {saved}")

        print()


if __name__ == "__main__":
    example_usage()