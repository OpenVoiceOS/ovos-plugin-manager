import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestTriplesTemplate(unittest.TestCase):
    def test_triples_extractor_init_with_config(self):
        from ovos_plugin_manager.templates.triples import TriplesExtractor
        config = {"first_person_token": "I"}

        # Create a concrete implementation for testing
        class ConcreteTriples(TriplesExtractor):
            def extract_triples(self, documents):
                return []

        extractor = ConcreteTriples(config=config)
        self.assertEqual(extractor.config, config)
        self.assertEqual(extractor.first_person_token, "I")

    def test_triples_extractor_init_without_config(self):
        from ovos_plugin_manager.templates.triples import TriplesExtractor

        # Create a concrete implementation for testing
        class ConcreteTriples(TriplesExtractor):
            def extract_triples(self, documents):
                return []

        extractor = ConcreteTriples()
        self.assertEqual(extractor.config, {})
        self.assertEqual(extractor.first_person_token, "USER")


class TestTriples(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TRIPLES
    CONFIG_TYPE = PluginConfigTypes.TRIPLES
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "triples"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.triples import find_triples_plugins
        find_triples_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.triples import load_triples_plugin
        load_triples_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

class TestTripleDataclasses(unittest.TestCase):
    def test_triple_as_tuple(self):
        from ovos_plugin_manager.templates.triples import Triple
        triple = Triple("subject", "predicate", "object", confidence=0.8, metadata={"key": "value"})
        self.assertEqual(triple.as_tuple(), ("subject", "predicate", "object"))
        self.assertEqual(triple.confidence, 0.8)
        self.assertEqual(triple.metadata, {"key": "value"})

    def test_triple_defaults(self):
        from ovos_plugin_manager.templates.triples import Triple
        triple = Triple("s", "p", "o")
        self.assertEqual(triple.confidence, 1.0)
        self.assertEqual(triple.metadata, {})

    def test_linked_entity(self):
        from ovos_plugin_manager.templates.triples import LinkedEntity
        entity = LinkedEntity("New York", 0, 8, "dbpedia:New_York", confidence=0.95)
        self.assertEqual(entity.mention, "New York")
        self.assertEqual(entity.start, 0)
        self.assertEqual(entity.end, 8)
        self.assertEqual(entity.entity_id, "dbpedia:New_York")
        self.assertEqual(entity.confidence, 0.95)

    def test_linked_triple_as_raw(self):
        from ovos_plugin_manager.templates.triples import LinkedTriple, LinkedEntity
        entity = LinkedEntity("New York", 0, 8, "dbpedia:New_York")
        lt = LinkedTriple("New York", "located_in", "USA", subject_entity=entity)
        self.assertEqual(lt.as_raw(), ("New York", "located_in", "USA"))
        self.assertIsNotNone(lt.subject_entity)
        self.assertIsNone(lt.object_entity)


class TestTriplesEntailmentValidation(unittest.TestCase):
    def test_validate_triple(self):
        from ovos_plugin_manager.templates.triples import TriplesEntailmentEngine, Triple

        class MockEngine(TriplesEntailmentEngine):
            def predict_entailment(self, premise, hypothesis, lang=None):
                # Return True if premise contains subject
                """
                Check whether the premise text contains the hypothesis's first element (case-insensitive).
                
                Parameters:
                    premise (str): Text used as the premise.
                    hypothesis (Sequence): Sequence where the first element is the hypothesis subject to match.
                    lang (str, optional): Language code (unused by this implementation).
                
                Returns:
                    true if the premise contains the hypothesis's first element (case-insensitive), false otherwise.
                """
                return hypothesis[0].lower() in premise.lower()

        engine = MockEngine()
        triple = Triple("Paris", "is_capital_of", "France")
        context_docs = ["Paris is the capital of France.", "Rome is beautiful."]

        self.assertTrue(engine.validate_triple(triple, context_docs))

    def test_validate_triple_no_match(self):
        from ovos_plugin_manager.templates.triples import TriplesEntailmentEngine, Triple

        class MockEngine(TriplesEntailmentEngine):
            def predict_entailment(self, premise, hypothesis, lang=None):
                """
                Default entailment predictor that never detects entailment.
                
                Parameters:
                    premise (str): Text serving as the premise/context against which entailment is evaluated.
                    hypothesis (str): Text representing the hypothesis to test for entailment from the premise.
                    lang (str, optional): Language code for the texts, if applicable.
                
                Returns:
                    bool: `True` if the premise entails the hypothesis, `False` otherwise. This default implementation always returns `False`.
                """
                return False

        engine = MockEngine()
        triple = Triple("London", "is_capital_of", "USA")
        context_docs = ["Paris is the capital of France."]

        self.assertFalse(engine.validate_triple(triple, context_docs))


class TestEntityLinker(unittest.TestCase):
    def test_link_entities_empty(self):
        from ovos_plugin_manager.templates.triples import EntityLinker

        class MockLinker(EntityLinker):
            def link_entities(self, text, lang=None):
                """
                Finds and returns entities mentioned in the provided text.
                
                Parameters:
                    text (str): The text to search for entity mentions.
                    lang (str | None): Optional language code to guide linking (e.g., "en").
                
                Returns:
                    list: A list of LinkedEntity objects representing detected entity mentions; an empty list if no entities are found.
                """
                return []

        linker = MockLinker()
        result = list(linker.link_triples([("subject", "predicate", "object")]))
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].subject_entity)
        self.assertIsNone(result[0].object_entity)

    def test_link_triples_with_entities(self):
        from ovos_plugin_manager.templates.triples import EntityLinker, LinkedEntity

        class MockLinker(EntityLinker):
            def link_entities(self, text, lang=None):
                """
                Link named entities found in the input text to external identifiers.
                
                Parameters:
                    text (str): The input text to search for entity mentions.
                    lang (str | None): Optional language code for linking; may be unused by implementations.
                
                Returns:
                    list[LinkedEntity]: A list of linked entities found in `text`. The list is empty if no entities are linked.
                """
                if "Paris" in text:
                    return [LinkedEntity(text, 0, len(text), f"dbpedia:{text}")]
                return []

        linker = MockLinker()
        result = list(linker.link_triples([("Paris", "capital_of", "France")]))
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].subject_entity)
        self.assertEqual(result[0].subject_entity.entity_id, "dbpedia:Paris")


class TestTriplesDB(unittest.TestCase):
    def test_triples_db_add_and_query(self):
        from ovos_plugin_manager.templates.triples import TriplesDB, Triple

        class InMemoryDB(TriplesDB):
            def __init__(self, config=None):
                """
                Initialize the in-memory triples database.
                
                Parameters:
                    config (dict | None): Optional configuration for the database instance.
                
                Description:
                    Calls the base initializer with `config` and creates an empty internal
                    mapping (self.triples) to store triples.
                """
                super().__init__(config)
                self.triples = {}

            def add(self, subject, predicate, obj, confidence=1.0, metadata=None):
                """
                Add a triple to the in-memory store and return the stored Triple object.
                
                Parameters:
                	subject (str): Subject of the triple.
                	predicate (str): Predicate/relationship of the triple.
                	obj (str): Object of the triple.
                	confidence (float): Confidence score for the triple; defaults to 1.0.
                	metadata (dict | None): Optional metadata to attach to the triple; treated as an empty dict when omitted.
                
                Returns:
                	Triple: The stored Triple instance representing (subject, predicate, object) with the provided confidence and metadata.
                """
                key = (subject, predicate, obj)
                triple = Triple(subject, predicate, obj, confidence, metadata or {})
                self.triples[key] = triple
                return triple

            def query(self, subject=None, predicate=None, obj=None):
                """
                Iterate stored triples filtered by optional subject, predicate, and object values.
                
                Parameters:
                	subject (str|None): Subject value to match, or None to match any subject.
                	predicate (str|None): Predicate value to match, or None to match any predicate.
                	obj (str|None): Object value to match, or None to match any object.
                
                Returns:
                	iterator: An iterator of Triple instances that match all provided filters.
                """
                for (s, p, o), triple in self.triples.items():
                    if (subject is None or s == subject) and \
                       (predicate is None or p == predicate) and \
                       (obj is None or o == obj):
                        yield triple

            def delete(self, subject=None, predicate=None, obj=None):
                """
                Delete triples that match the given optional filters.
                
                Parameters:
                    subject (str|None): Subject to match, or None to match any subject.
                    predicate (str|None): Predicate to match, or None to match any predicate.
                    obj (str|None): Object to match, or None to match any object.
                
                Returns:
                    int: Number of triples removed.
                """
                to_delete = []
                for (s, p, o) in self.triples.keys():
                    if (subject is None or s == subject) and \
                       (predicate is None or p == predicate) and \
                       (obj is None or o == obj):
                        to_delete.append((s, p, o))
                for key in to_delete:
                    del self.triples[key]
                return len(to_delete)

            def count(self):
                """
                Return the number of triples currently stored in the database.
                
                Returns:
                    int: The count of stored triples.
                """
                return len(self.triples)

        db = InMemoryDB()
        triple = db.add("Paris", "capital_of", "France")
        self.assertEqual(triple.subject, "Paris")
        self.assertEqual(db.count(), 1)

        results = list(db.query(subject="Paris"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].predicate, "capital_of")

    def test_triples_db_add_batch(self):
        """
        Verify that TriplesDB.add_batch inserts multiple triples and returns them.
        
        Asserts that the number of returned triples equals the input batch size and that the database count reflects the added triples.
        """
        from ovos_plugin_manager.templates.triples import TriplesDB

        class InMemoryDB(TriplesDB):
            def __init__(self, config=None):
                """
                Initialize the in-memory triples database.
                
                Parameters:
                    config (dict, optional): Configuration for the database or plugin. If omitted, defaults from the base class are used.
                
                Notes:
                    Creates an empty `self.triples` list to hold stored Triple objects.
                """
                super().__init__(config)
                self.triples = []

            def add(self, subject, predicate, obj, confidence=1.0, metadata=None):
                """
                Add a triple to the in-memory store and return the created Triple object.
                
                Parameters:
                	subject (str): Subject of the triple.
                	predicate (str): Predicate of the triple.
                	obj (str): Object of the triple.
                	confidence (float): Confidence score for the triple, defaults to 1.0.
                	metadata (dict | None): Optional additional metadata for the triple.
                
                Returns:
                	Triple: The stored Triple instance with the provided fields.
                """
                from ovos_plugin_manager.templates.triples import Triple
                triple = Triple(subject, predicate, obj, confidence, metadata or {})
                self.triples.append(triple)
                return triple

            def query(self, subject=None, predicate=None, obj=None):
                """
                Return triples that match the provided subject, predicate, and/or object filters.
                
                Parameters:
                    subject (str | None): Subject value to match; if None, do not filter by subject.
                    predicate (str | None): Predicate value to match; if None, do not filter by predicate.
                    obj (str | None): Object value to match; if None, do not filter by object.
                
                Returns:
                    list[Triple]: List of triples matching all provided filters.
                """
                return []

            def delete(self, subject=None, predicate=None, obj=None):
                """
                Delete triples matching the provided subject, predicate, and/or object filters.
                
                Parameters:
                	subject (str | None): Subject filter; only triples with this subject will be deleted. If None, subject is not filtered.
                	predicate (str | None): Predicate filter; only triples with this predicate will be deleted. If None, predicate is not filtered.
                	obj (str | None): Object filter; only triples with this object will be deleted. If None, object is not filtered.
                
                Returns:
                	int: Number of triples removed.
                """
                return 0

            def count(self):
                """
                Return the number of triples currently stored in the database.
                
                Returns:
                    int: The count of stored triples.
                """
                return len(self.triples)

        db = InMemoryDB()
        batch = [("s1", "p1", "o1"), ("s2", "p2", "o2")]
        results = db.add_batch(batch)
        self.assertEqual(len(results), 2)
        self.assertEqual(db.count(), 2)


class TestTriplesReasoner(unittest.TestCase):
    def test_reasoner_infer(self):
        from ovos_plugin_manager.templates.triples import TriplesReasoner, Triple

        class ReversalReasoner(TriplesReasoner):
            def infer(self, triples):
                """
                Infer inverse triples from the provided triples.
                
                Parameters:
                    triples (Iterable[Triple]): An iterable of triples to infer from.
                
                Returns:
                    Iterator[Triple]: Yields a Triple for each input where the subject is the original's object, the predicate is "inverse_of_" + original predicate, and the object is the original's subject.
                """
                for triple in triples:
                    yield Triple(triple.obj, "inverse_of_" + triple.predicate, triple.subject)

        reasoner = ReversalReasoner()
        input_triples = [Triple("Paris", "capital_of", "France")]
        inferred = list(reasoner.infer(input_triples))
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].subject, "France")

    def test_extract_and_infer(self):
        """
        Verify that TriplesReasoner.extract_and_infer runs a TriplesExtractor and yields both extracted and inferred triples.
        
        Defines a simple extractor that yields one raw triple per document and a reasoner that inverts each triple; calling extract_and_infer with a single document produces one extracted triple and one inferred triple.
        """
        from ovos_plugin_manager.templates.triples import TriplesReasoner, TriplesExtractor, Triple

        class SimplExtractor(TriplesExtractor):
            def extract_triples(self, documents):
                """
                Extract triples from each input document.
                
                Parameters:
                    documents (iterable): Sequence of documents (e.g., strings) to process.
                
                Returns:
                    iterator: Yields raw triples as (subject, predicate, object) tuples extracted from the provided documents.
                """
                for doc in documents:
                    yield ("A", "relates_to", "B")

        class SimpleReasoner(TriplesReasoner):
            def infer(self, triples):
                """
                Infer inverse triples by swapping each triple's subject and object and using the predicate "relates_to".
                
                Parameters:
                    triples (Iterable[Triple]): An iterable of Triple objects to process.
                
                Returns:
                    Iterator[Triple]: Yields a new Triple for each input with subject set to the original object, predicate set to "relates_to", and object set to the original subject.
                """
                for triple in triples:
                    yield Triple(triple.obj, "relates_to", triple.subject)

        extractor = SimplExtractor()
        reasoner = SimpleReasoner()
        results = list(reasoner.extract_and_infer(extractor, ["doc1"]))
        self.assertEqual(len(results), 2)  # 1 extracted + 1 inferred


class TestNewPluginTypes(unittest.TestCase):
    def test_plugin_types_exist(self):
        self.assertEqual(PluginTypes.ENTITY_LINKER, "opm.entity_linker")
        self.assertEqual(PluginTypes.TRIPLES_STORE, "opm.triples.store")
        self.assertEqual(PluginTypes.TRIPLES_REASONER, "opm.triples.reasoner")

    def test_plugin_config_types_exist(self):
        self.assertEqual(PluginConfigTypes.ENTITY_LINKER, "opm.entity_linker.config")
        self.assertEqual(PluginConfigTypes.TRIPLES_STORE, "opm.triples.store.config")
        self.assertEqual(PluginConfigTypes.TRIPLES_REASONER, "opm.triples.reasoner.config")


class TestTriplesStoreFunctions(unittest.TestCase):
    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_triples_store_plugins(self, find_plugins):
        from ovos_plugin_manager.triples import find_triples_store_plugins
        find_triples_store_plugins()
        find_plugins.assert_called_once_with(PluginTypes.TRIPLES_STORE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_triples_store_plugin(self, load_plugin):
        from ovos_plugin_manager.triples import load_triples_store_plugin
        load_triples_store_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", PluginTypes.TRIPLES_STORE)

class TestTriplesReasonerFunctions(unittest.TestCase):
    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_triples_reasoner_plugins(self, find_plugins):
        from ovos_plugin_manager.triples import find_triples_reasoner_plugins
        find_triples_reasoner_plugins()
        find_plugins.assert_called_once_with(PluginTypes.TRIPLES_REASONER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_triples_reasoner_plugin(self, load_plugin):
        from ovos_plugin_manager.triples import load_triples_reasoner_plugin
        load_triples_reasoner_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", PluginTypes.TRIPLES_REASONER)

class TestEntityLinkerFunctions(unittest.TestCase):
    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_entity_linker_plugins(self, find_plugins):
        from ovos_plugin_manager.triples import find_entity_linker_plugins
        find_entity_linker_plugins()
        find_plugins.assert_called_once_with(PluginTypes.ENTITY_LINKER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_entity_linker_plugin(self, load_plugin):
        from ovos_plugin_manager.triples import load_entity_linker_plugin
        load_entity_linker_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", PluginTypes.ENTITY_LINKER)
