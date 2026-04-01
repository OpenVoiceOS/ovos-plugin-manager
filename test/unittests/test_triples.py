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
                return hypothesis[0].lower() in premise.lower()

        engine = MockEngine()
        triple = Triple("Paris", "is_capital_of", "France")
        context_docs = ["Paris is the capital of France.", "Rome is beautiful."]

        self.assertTrue(engine.validate_triple(triple, context_docs))

    def test_validate_triple_no_match(self):
        from ovos_plugin_manager.templates.triples import TriplesEntailmentEngine, Triple

        class MockEngine(TriplesEntailmentEngine):
            def predict_entailment(self, premise, hypothesis, lang=None):
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
                super().__init__(config)
                self.triples = {}

            def add(self, subject, predicate, obj, confidence=1.0, metadata=None):
                key = (subject, predicate, obj)
                triple = Triple(subject, predicate, obj, confidence, metadata or {})
                self.triples[key] = triple
                return triple

            def query(self, subject=None, predicate=None, obj=None):
                for (s, p, o), triple in self.triples.items():
                    if (subject is None or s == subject) and \
                       (predicate is None or p == predicate) and \
                       (obj is None or o == obj):
                        yield triple

            def delete(self, subject=None, predicate=None, obj=None):
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
                return len(self.triples)

        db = InMemoryDB()
        triple = db.add("Paris", "capital_of", "France")
        self.assertEqual(triple.subject, "Paris")
        self.assertEqual(db.count(), 1)

        results = list(db.query(subject="Paris"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].predicate, "capital_of")

    def test_triples_db_add_batch(self):
        from ovos_plugin_manager.templates.triples import TriplesDB

        class InMemoryDB(TriplesDB):
            def __init__(self, config=None):
                super().__init__(config)
                self.triples = []

            def add(self, subject, predicate, obj, confidence=1.0, metadata=None):
                from ovos_plugin_manager.templates.triples import Triple
                triple = Triple(subject, predicate, obj, confidence, metadata or {})
                self.triples.append(triple)
                return triple

            def query(self, subject=None, predicate=None, obj=None):
                return []

            def delete(self, subject=None, predicate=None, obj=None):
                return 0

            def count(self):
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
                for triple in triples:
                    yield Triple(triple.obj, "inverse_of_" + triple.predicate, triple.subject)

        reasoner = ReversalReasoner()
        input_triples = [Triple("Paris", "capital_of", "France")]
        inferred = list(reasoner.infer(input_triples))
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].subject, "France")

    def test_extract_and_infer(self):
        from ovos_plugin_manager.templates.triples import TriplesReasoner, TriplesExtractor, Triple

        class SimplExtractor(TriplesExtractor):
            def extract_triples(self, documents):
                for doc in documents:
                    yield ("A", "relates_to", "B")

        class SimpleReasoner(TriplesReasoner):
            def infer(self, triples):
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
