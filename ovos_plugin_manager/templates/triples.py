# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Plugin templates for semantic triple extraction, storage, reasoning, and entity linking."""
import abc
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Type alias for raw triples (subject, predicate, object)
RawTriple = Tuple[str, str, str]


@dataclass
class Triple:
    """A stored triple with provenance metadata."""
    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_tuple(self) -> RawTriple:
        """Return the triple as a raw (subject, predicate, object) tuple."""
        return (self.subject, self.predicate, self.obj)


@dataclass
class LinkedEntity:
    """A resolved entity mention within a text span."""
    mention: str
    start: int
    end: int
    entity_id: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkedTriple:
    """
    A raw triple decorated with entity-linking results for subject and object.
    The predicate is left as a plain string since predicates are relational labels,
    not entity mentions.
    """
    subject: str
    predicate: str
    obj: str
    subject_entity: Optional[LinkedEntity] = None
    object_entity: Optional[LinkedEntity] = None

    def as_raw(self) -> RawTriple:
        """Return the triple as a raw (subject, predicate, object) tuple."""
        return (self.subject, self.predicate, self.obj)


class TriplesExtractor:
    """Base class for plugins that extract semantic triples from documents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.first_person_token = self.config.get("first_person_token", "USER")

    @abc.abstractmethod
    def extract_triples(self, documents: List[str]) -> Iterable[RawTriple]:
        """Extract semantic triples from a list of documents.

        Args:
            documents: List of text documents.

        Yields:
            Raw triples as (subject, predicate, object) tuples.
        """
        raise NotImplementedError


class TriplesEntailmentEngine:
    """
    Engine for Natural Language Inference (NLI) validation.

    Determines if a hypothesis (triple) is logically supported by a premise (text).
    Used as a validator for extracted triples against source documents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    def predict_entailment(self, premise: str,
                           hypothesis: RawTriple,
                           lang: Optional[str] = None) -> bool:
        """Determine if the premise logically entails the hypothesis triple.

        Args:
            premise: Base statement or source text.
            hypothesis: Triple (subject, predicate, object) to verify.
            lang: Optional BCP-47 language code.

        Returns:
            True if the premise entails the hypothesis, False otherwise.
        """
        raise NotImplementedError

    def validate_triple(self,
                        triple: Triple,
                        context_docs: List[str],
                        lang: Optional[str] = None) -> bool:
        """Check if a stored Triple is consistent with any context document.

        Iterates over context_docs and returns True on the first entailment found.
        Returns False if no document entails the triple.

        Args:
            triple: Triple object to validate.
            context_docs: List of premise strings to test against.
            lang: Optional language code.

        Returns:
            bool: True if any context doc entails the triple.
        """
        for doc in context_docs:
            if self.predict_entailment(doc, triple.as_tuple(), lang=lang):
                return True
        return False


class EntityLinker:
    """Base class for plugins that link entity mentions to canonical IDs."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    def link_entities(self, text: str,
                      lang: Optional[str] = None) -> List[LinkedEntity]:
        """Identify entity mentions in text and resolve them to canonical IDs.

        Args:
            text: Input text.
            lang: Optional BCP-47 language code.

        Returns:
            List of LinkedEntity results, ordered by mention start offset.
        """
        raise NotImplementedError

    def link_triples(self,
                     triples: Iterable[RawTriple],
                     lang: Optional[str] = None) -> Iterable[LinkedTriple]:
        """Link subject and object entities for each triple.

        Calls link_entities on subject and object strings separately.
        Subclasses may override for more efficient full-sentence linking.

        Args:
            triples: Iterable of (subject, predicate, object) raw triples.
            lang: Optional language code.

        Yields:
            LinkedTriple for each input triple (may have None entities).
        """
        for subject, predicate, obj in triples:
            subj_entities = self.link_entities(subject, lang=lang)
            obj_entities = self.link_entities(obj, lang=lang)
            yield LinkedTriple(
                subject=subject,
                predicate=predicate,
                obj=obj,
                subject_entity=subj_entities[0] if subj_entities else None,
                object_entity=obj_entities[0] if obj_entities else None,
            )


class TriplesDB:
    """
    Abstract storage backend for triples with wildcard query support.

    Abstract methods define the minimal CRUD interface. Concrete batch wrappers
    loop over single-item methods by default; subclasses may override for
    bulk-optimised implementations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    def add(self,
            subject: str,
            predicate: str,
            obj: str,
            confidence: float = 1.0,
            metadata: Optional[Dict[str, Any]] = None) -> Triple:
        """Persist a single triple.

        Args:
            subject: Triple subject.
            predicate: Triple predicate.
            obj: Triple object.
            confidence: Confidence score (0–1).
            metadata: Optional metadata dict.

        Returns:
            Triple: The stored triple object.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query(self,
              subject: Optional[str] = None,
              predicate: Optional[str] = None,
              obj: Optional[str] = None) -> Iterable[Triple]:
        """Retrieve triples matching a pattern.

        None in any position is a wildcard. At least one of subject/predicate/obj
        should be provided.

        Args:
            subject: Subject to match (None = wildcard).
            predicate: Predicate to match (None = wildcard).
            obj: Object to match (None = wildcard).

        Yields:
            Triple objects matching the pattern.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self,
               subject: Optional[str] = None,
               predicate: Optional[str] = None,
               obj: Optional[str] = None) -> int:
        """Delete triples matching a pattern.

        Args:
            subject: Subject to match (None = wildcard).
            predicate: Predicate to match (None = wildcard).
            obj: Object to match (None = wildcard).

        Returns:
            int: Number of deleted triples.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count(self) -> int:
        """Return total number of stored triples.

        Returns:
            int: Total count.
        """
        raise NotImplementedError

    def add_batch(self,
                  triples: Iterable[RawTriple],
                  confidences: Optional[List[float]] = None,
                  metadata: Optional[List[Optional[Dict[str, Any]]]] = None
                  ) -> List[Triple]:
        """Persist multiple triples.

        Default implementation loops over add(); subclasses may override
        for bulk-insert efficiency.

        Args:
            triples: Iterable of (subject, predicate, object).
            confidences: Per-triple confidence scores (default 1.0 each).
            metadata: Per-triple metadata dicts (default None each).

        Returns:
            List of stored Triple objects in input order.
        """
        triples_list = list(triples)
        if confidences is None:
            confidences = [1.0] * len(triples_list)
        if metadata is None:
            metadata = [None] * len(triples_list)
        return [
            self.add(s, p, o, conf, meta)
            for (s, p, o), conf, meta in zip(triples_list, confidences, metadata)
        ]

    def delete_batch(self,
                     patterns: Iterable[Tuple[Optional[str],
                                              Optional[str],
                                              Optional[str]]]) -> int:
        """Delete triples for multiple patterns.

        Default implementation loops over delete(); subclasses may override.

        Args:
            patterns: Iterable of (subject, predicate, object) patterns
                      where None is a wildcard.

        Returns:
            int: Total count of deleted triples across all patterns.
        """
        return sum(self.delete(s, p, o) for s, p, o in patterns)


class TriplesReasoner:
    """
    Abstract base for inference engines that derive new triples from existing ones.

    Intentionally decoupled from TriplesDB: the reasoner operates on plain iterables
    and does not know how triples are stored. Callers are responsible for persisting
    inferred triples via TriplesDB.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    def infer(self, triples: Iterable[Triple]) -> Iterable[Triple]:
        """Derive new triples from the provided set.

        Args:
            triples: Iterable of input Triple objects (may be a one-pass iterator).

        Yields:
            Newly inferred Triple objects. Must NOT yield duplicates of input triples.
        """
        raise NotImplementedError

    def extract_and_infer(self,
                          extractor: TriplesExtractor,
                          documents: List[str]) -> Iterable[Triple]:
        """Convenience chain: extract triples from documents, then run inference.

        Args:
            extractor: A TriplesExtractor instance.
            documents: Source documents.

        Yields:
            All extracted triples followed by all inferred triples.
        """
        raw_triples = list(extractor.extract_triples(documents))
        base_triples = [Triple(s, p, o) for s, p, o in raw_triples]
        yield from base_triples
        yield from self.infer(base_triples)
