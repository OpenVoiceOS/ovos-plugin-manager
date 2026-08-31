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
        """
        Return a raw triple containing the subject, predicate, and object.
        
        Returns:
            RawTriple: Tuple in the form (subject, predicate, object).
        """
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
        """
        Return the triple as a raw (subject, predicate, object) tuple.
        
        Returns:
            RawTriple: A 3-tuple containing (subject, predicate, object).
        """
        return (self.subject, self.predicate, self.obj)


class TriplesExtractor:
    """Base class for plugins that extract semantic triples from documents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the extractor with optional configuration.
        
        Parameters:
            config (Optional[Dict[str, Any]]): Configuration mapping. May include the key
                "first_person_token" to override the default token used to represent the
                first-person subject in extracted triples (default: "USER").
        
        """
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
        """
        Initialize the instance with an optional configuration mapping.
        
        Parameters:
            config: Optional mapping of configuration options for the instance; defaults to an empty dictionary when not provided.
        """
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
        """
        Initialize the instance with an optional configuration mapping.
        
        Parameters:
            config: Optional mapping of configuration options for the instance; defaults to an empty dictionary when not provided.
        """
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
        """
        Link subject and object entities for each triple.

        Yields a LinkedTriple for each input raw triple with the original subject, predicate, and object; the subject_entity and object_entity fields will be the first resolved entity for the corresponding span when available, otherwise None. Subclasses may override to provide more efficient or context-aware linking (for example, full-sentence linking).

        Parameters:
            triples (Iterable[RawTriple]): Iterable of (subject, predicate, object) raw triples.
            lang (Optional[str]): Optional language code.

        Returns:
            Iterable[LinkedTriple]: An iterator that yields a LinkedTriple for each input triple; entity fields may be None.
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
        """
        Initialize the instance with an optional configuration mapping.
        
        Parameters:
            config: Optional mapping of configuration options for the instance; defaults to an empty dictionary when not provided.
        """
        self.config = config or {}

    @abc.abstractmethod
    def add(self,
            subject: str,
            predicate: str,
            obj: str,
            confidence: float = 1.0,
            metadata: Optional[Dict[str, Any]] = None) -> Triple:
        """
        Store a single triple in the backend.

        Parameters:
            subject (str): Triple subject.
            predicate (str): Triple predicate.
            obj (str): Triple object.
            confidence (float): Confidence score between 0 and 1. Defaults to 1.0.
            metadata (Optional[Dict[str, Any]]): Optional metadata associated with the triple.

        Returns:
            Triple: The stored triple object.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query(self,
              subject: Optional[str] = None,
              predicate: Optional[str] = None,
              obj: Optional[str] = None) -> Iterable[Triple]:
        """
        Retrieve triples that match the given pattern.

        None in any position acts as a wildcard; at least one of `subject`, `predicate`, or `obj` must be provided.

        Parameters:
            subject: Subject to match (None = wildcard).
            predicate: Predicate to match (None = wildcard).
            obj: Object to match (None = wildcard).

        Yields:
            Triple objects that satisfy the provided pattern.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self,
               subject: Optional[str] = None,
               predicate: Optional[str] = None,
               obj: Optional[str] = None) -> int:
        """
        Delete stored triples that match the provided subject/predicate/object pattern.

        A `None` value for any parameter acts as a wildcard for that position.

        Parameters:
            subject (Optional[str]): Subject to match (None = wildcard).
            predicate (Optional[str]): Predicate to match (None = wildcard).
            obj (Optional[str]): Object to match (None = wildcard).

        Returns:
            int: Number of triples deleted.
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
        """
        Persist multiple triples in the storage backend.

        This default implementation materializes the input iterable and calls self.add(...) for each triple in order; subclasses may override to provide a more efficient bulk-insert.

        Parameters:
            triples (Iterable[RawTriple]): Iterable of (subject, predicate, object) tuples to store.
            confidences (Optional[List[float]]): Per-triple confidence scores; if omitted, each triple uses 1.0.
            metadata (Optional[List[Optional[Dict[str, Any]]]]): Per-triple metadata dicts; if omitted, each triple uses None.

        Returns:
            List[Triple]: Stored Triple objects in the same order as the input triples.
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
        """
        Delete triples matching each provided (subject, predicate, object) pattern.

        Each pattern is a tuple where None acts as a wildcard and will match any value; the method deletes all triples that match each pattern and returns the total number removed.

        Parameters:
            patterns (Iterable[Tuple[Optional[str], Optional[str], Optional[str]]]): Iterable of (subject, predicate, object) patterns; use None as a wildcard.

        Returns:
            int: Total number of triples deleted across all provided patterns.
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
        """
        Initialize the instance with an optional configuration mapping.
        
        Parameters:
            config: Optional mapping of configuration options for the instance; defaults to an empty dictionary when not provided.
        """
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
        """
        Extract triples from the provided documents using the given extractor, yield the extracted triples, then yield triples inferred from those extracted triples.

        Parameters:
            extractor (TriplesExtractor): Extractor used to produce raw triples from documents.
            documents (List[str]): Source documents to extract triples from.

        Returns:
            Iterable[Triple]: Yields extracted Triple instances in input order followed by Triple instances produced by the reasoner's inference.
        """
        raw_triples = list(extractor.extract_triples(documents))
        base_triples = [Triple(s, p, o) for s, p, o in raw_triples]
        yield from base_triples
        yield from self.infer(base_triples)
