import abc

from typing import Tuple, List, Iterable


class TriplesExtractor:

    def __init__(self, config=None):
        self.config = config or {}
        self.first_person_token = self.config.get("first_person_token", "USER")

    @abc.abstractmethod
    def extract_triples(self, documents: List[str]) -> Iterable[Tuple[str, str, str]]:
        """Extract semantic triples from a list of documents."""
