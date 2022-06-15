from ovos_utils.messagebus import get_message_lang


class KeywordExtractor:
    def __init__(self, config=None):
        self.config = config or {}

    @property
    def lang(self):
        return get_message_lang()

    def extract(self, text):
        return {text: 0.0}
