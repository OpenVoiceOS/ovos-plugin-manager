import abc
import inspect
from functools import wraps
from typing import Optional, List, Iterable, Tuple, Dict, Union, Any

from json_database import JsonStorageXDG
from ovos_utils.log import LOG, log_deprecation
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.xdg_utils import xdg_cache_home

from ovos_plugin_manager.templates.language import LanguageTranslator, LanguageDetector
from ovos_plugin_manager.thirdparty.solvers import AbstractSolver


def auto_translate(translate_keys: List[str], translate_str_args=True):
    """ Decorator to ensure all kwargs in 'translate_keys' are translated to self.default_lang.
    data returned by the decorated function will be translated back to original language
     NOTE: not meant to be used outside solver plugins"""

    def func_decorator(func):

        @wraps(func)
        def func_wrapper(*args, **kwargs):
            solver: AbstractSolver = args[0]
            # check if translation is enabled
            if not solver.enable_tx:
                return func(*args, **kwargs)

            lang = kwargs.get("lang")
            if lang:
                lang = standardize_lang_tag(lang)
            # check if translation can be skipped
            if any([lang is None,
                    lang == solver.default_lang,
                    lang in solver.supported_langs]):
                LOG.debug(f"skipping translation, 'lang': {lang} is supported by {func}")
                return func(*args, **kwargs)

            # translate string arguments
            if translate_str_args:
                args = list(args)
                for idx, arg in enumerate(args):
                    if isinstance(arg, str):
                        LOG.debug(
                            f"translating string argument with index: '{idx}' from {lang} to {solver.default_lang} for func: {func}")
                        args[idx] = _do_tx(solver, arg,
                                           source_lang=lang,
                                           target_lang=solver.default_lang)

            # translate input keys
            for k in translate_keys:
                v = kwargs.get(k)
                if not v:
                    continue
                kwargs[k] = _do_tx(solver, v,
                                   source_lang=lang,
                                   target_lang=solver.default_lang)

            out = func(*args, **kwargs)

            # reverse translate
            return _do_tx(solver, out,
                          source_lang=solver.default_lang,
                          target_lang=lang)

        return func_wrapper

    return func_decorator


def auto_detect_lang(text_keys: List[str]):
    """ Decorator to auto detect language if needed
    NOTE: requires "lang" argument, not meant to be used outside solver plugins"""

    def func_decorator(func):

        @wraps(func)
        def func_wrapper(*args, **kwargs):
            solver: AbstractSolver = args[0]

            # detect language if needed
            lang = kwargs.get("lang")
            if lang is None:
                LOG.debug(f"'lang' missing in kwargs for func: {func}")
                for k in text_keys:
                    v = kwargs.get(k)
                    if isinstance(v, str):
                        lang = solver.detect_language(v)
                        LOG.debug(f"detected 'lang': {lang} in key: '{k}' for func: {func}")
                        break
                else:
                    for idx, v in enumerate(args):
                        if isinstance(v, str) and len(v.split(" ")) > 1:
                            lang = solver.detect_language(v)
                            LOG.debug(f"detected 'lang': {lang} in argument '{idx}' for func: {func}")

            if lang:
                lang = standardize_lang_tag(lang)
            kwargs["lang"] = lang
            return func(*args, **kwargs)

        return func_wrapper

    return func_decorator


def _deprecate_context2lang():
    """Decorator to deprecate the 'context' kwarg and replace it with 'lang'.
    NOTE: can only be used in methods that accept "lang" as argument"""

    def func_decorator(func):

        @wraps(func)
        def func_wrapper(*args, **kwargs):

            # Inspect the function signature to ensure it has both 'lang' and 'context' parameters
            signature = inspect.signature(func)
            params = signature.parameters

            if "context" in kwargs:
                # NOTE: deprecate this at same time we
                # standardize plugin namespaces to opm.XXX
                log_deprecation("'context' kwarg has been deprecated, "
                                "please pass 'lang' as it's own kwarg instead", "1.0.0")
                if "lang" in kwargs["context"] and "lang" not in kwargs:
                    kwargs["lang"] = kwargs["context"]["lang"]

            # ensure valid kwargs
            if "lang" not in params and "lang" in kwargs:
                kwargs.pop("lang")
            if "context" not in params and "context" in kwargs:
                kwargs.pop("context")
            return func(*args, **kwargs)

        return func_wrapper

    return func_decorator


class QuestionSolver(AbstractSolver):
    """
    A solver for free-form, unconstrained spoken questions that handles automatic translation as needed.
    """

    def __init__(self, config: Optional[Dict] = None,
                 translator: Optional[LanguageTranslator] = None,
                 detector: Optional[LanguageDetector] = None,
                 priority: int = 50,
                 enable_tx: bool = False,
                 enable_cache: bool = False,
                 internal_lang: Optional[str] = None,
                 *args, **kwargs):
        """
        Initialize the QuestionSolver.

        Args:
            config (Optional[Dict]): Optional configuration dictionary.
            translator (Optional[LanguageTranslator]): Optional language translator.
            detector (Optional[LanguageDetector]): Optional language detector.
            priority (int): Priority of the solver.
            enable_tx (bool): Flag to enable translation.
            enable_cache (bool): Flag to enable caching.
            internal_lang (Optional[str]): Internal language code. Defaults to None.
        """
        super().__init__(config, translator, detector, priority,
                         enable_tx, enable_cache, internal_lang,
                         *args, **kwargs)
        name = kwargs.get("name") or self.__class__.__name__
        if self.enable_cache:
            # cache contains raw data
            self.cache = JsonStorageXDG(name + "_data",
                                        xdg_folder=xdg_cache_home(),
                                        subfolder="ovos_solvers")
            # spoken cache contains dialogs
            self.spoken_cache = JsonStorageXDG(name,
                                               xdg_folder=xdg_cache_home(),
                                               subfolder="ovos_solvers")
        else:
            self.cache = self.spoken_cache = {}

    # plugin methods to override
    @abc.abstractmethod
    def get_spoken_answer(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None) -> Optional[str]:
        """
        Obtain the spoken answer for a given query.

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            str: The spoken answer as a text response.
        """
        raise NotImplementedError

    @_deprecate_context2lang()
    def stream_utterances(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None) -> Iterable[str]:
        """
        Stream utterances for the given query as they become available.

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            Iterable[str]: An iterable of utterances.
        """
        ans = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)
        for utt in self.sentence_split(ans):
            yield utt

    @_deprecate_context2lang()
    def get_data(self, query: str,
                 lang: Optional[str] = None,
                 units: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Retrieve data for the given query.

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            Optional[Dict]: A dictionary containing the answer.
        """
        return {"answer": _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)}

    @_deprecate_context2lang()
    def get_image(self, query: str,
                  lang: Optional[str] = None,
                  units: Optional[str] = None) -> Optional[str]:
        """
        Get the path or URL to an image associated with the query.

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            Optional[str]: The path or URL to a single image.
        """
        return None

    @_deprecate_context2lang()
    def get_expanded_answer(self, query: str,
                            lang: Optional[str] = None,
                            units: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get an expanded list of steps to elaborate on the answer.

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            List[Dict]: A list of dictionaries with each step containing a title, summary, and optional image.
        """
        return [{"title": query,
                 "summary": _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units),
                 "img": _call_with_sanitized_kwargs(self.get_image, query, lang=lang, units=units)}]

    # user facing methods
    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def search(self, query: str,
               lang: Optional[str] = None,
               units: Optional[str] = None) -> Optional[Dict]:
        """
        Perform a search with automatic translation and caching.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            Dict: The data dictionary retrieved from the cache or computed anew.
        """
        # read from cache
        if self.enable_cache and query in self.cache:
            data = self.cache[query]
        else:
            # search data
            try:
                data = _call_with_sanitized_kwargs(self.get_data, query, lang=lang, units=units)
            except:
                return {}

        # save to cache
        if self.enable_cache:
            self.cache[query] = data
            self.cache.store()
        return data

    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def visual_answer(self, query: str,
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> Optional[str]:
        """
        Retrieve the image associated with the query with automatic translation and caching.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            str: The path or URL to the image.
        """
        return _call_with_sanitized_kwargs(self.get_image, query, lang=lang, units=units)

    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def spoken_answer(self, query: str,
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> Optional[str]:
        """
        Retrieve the spoken answer for the query with automatic translation and caching.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            str: The spoken answer as a text response.
        """
        # get answer
        if self.enable_cache and query in self.spoken_cache:
            # read from cache
            summary = self.spoken_cache[query]
        else:

            summary = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)
            # save to cache
            if self.enable_cache:
                self.spoken_cache[query] = summary
                self.spoken_cache.store()
        return summary

    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def long_answer(self, query: str,
                    lang: Optional[str] = None,
                    units: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Retrieve a detailed list of steps to expand the answer.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            List[Dict]: A list of steps to elaborate on the answer, with each step containing a title, summary, and optional image.
        """
        steps = _call_with_sanitized_kwargs(self.get_expanded_answer, query, lang=lang, units=units)
        # use spoken_answer as last resort
        if not steps:
            summary = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)
            if summary:
                img = _call_with_sanitized_kwargs(self.get_image, query, lang=lang, units=units)
                steps = [{"title": query, "summary": step, "img": img} for step in self.sentence_split(summary, -1)]
        return steps


class CorpusSolver(QuestionSolver):
    """Retrieval based question solver"""

    def __init__(self, config=None,
                 translator: Optional[LanguageTranslator] = None,
                 detector: Optional[LanguageDetector] = None,
                 priority: int = 50,
                 enable_tx: bool = False,
                 enable_cache: bool = False,
                 *args, **kwargs):
        super().__init__(config, translator, detector,
                         priority, enable_tx, enable_cache,
                         *args, **kwargs)
        LOG.debug(f"corpus presumed to be in language: {self.default_lang}")

    @abc.abstractmethod
    def load_corpus(self, corpus: List[str]):
        """index the provided list of sentences"""

    @abc.abstractmethod
    def query(self, query: str, lang: Optional[str], k: int = 3) -> Iterable[Tuple[str, float]]:
        """return top_k matches from indexed corpus"""

    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def retrieve_from_corpus(self, query: str, k: int = 3, lang: Optional[str] = None) -> List[Tuple[float, str]]:
        """return top_k matches from indexed corpus"""
        res = []
        for doc, score in self.query(query, lang, k=k):
            LOG.debug(f"Rank {len(res) + 1} (score: {score}): {doc}")
            if self.config.get("min_conf"):
                if score >= self.config["min_conf"]:
                    res.append((score, doc))
            else:
                res.append((score, doc))
        return res

    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def get_spoken_answer(self, query: str, lang: Optional[str] = None) -> Optional[str]:
        # Query the corpus
        answers = [a[1] for a in self.retrieve_from_corpus(query, lang=lang,
                                                           k=self.config.get("n_answer", 1))]
        if answers:
            return ". ".join(answers[:self.config.get("n_answer", 1)])


class QACorpusSolver(CorpusSolver):
    def __init__(self, config=None,
                 translator: Optional[LanguageTranslator] = None,
                 detector: Optional[LanguageDetector] = None,
                 priority: int = 50,
                 enable_tx: bool = False,
                 enable_cache: bool = False,
                 *args, **kwargs):
        self.answers = {}
        super().__init__(config, translator, detector,
                         priority, enable_tx, enable_cache,
                         *args, **kwargs)

    def load_corpus(self, corpus: Dict):
        self.answers = corpus
        super().load_corpus(list(self.answers.keys()))

    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def retrieve_from_corpus(self, query: str, k: int = 1, lang: Optional[str] = None) -> List[Tuple[float, str]]:
        res = []
        for doc, score in super().retrieve_from_corpus(query, k, lang):
            LOG.debug(f"Answer {len(res) + 1} (score: {score}): {self.answers[doc]}")
            res.append((score, self.answers[doc]))
        return res


class TldrSolver(AbstractSolver):
    """
    Solver for performing NLP summarization tasks,
    handling automatic translation as needed.
    """

    @abc.abstractmethod
    def get_tldr(self, document: str,
                 lang: Optional[str] = None) -> str:
        """
        Summarize the provided document.

        :param document: The text of the document to summarize, assured to be in the default language.
        :param lang: Optional language code.
        :return: A summary of the provided document.
        """
        raise NotImplementedError

    # user facing methods

    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["document"])
    @auto_translate(translate_keys=["document"])
    def tldr(self, document: str, lang: Optional[str] = None) -> str:
        """
        Summarize the provided document with automatic translation and caching if needed.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "document"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param document: The text of the document to summarize.
        :param lang: Optional language code.
        :return: A summary of the provided document.
        """
        # summarize
        return _call_with_sanitized_kwargs(self.get_tldr, document, lang=lang)


class EvidenceSolver(AbstractSolver):
    """
    Solver for NLP reading comprehension tasks,
    handling automatic translation as needed.
    """

    @abc.abstractmethod
    def get_best_passage(self, evidence: str, question: str,
                         lang: Optional[str] = None) -> str:
        """
        Extract the best passage from evidence that answers the given question.

        :param evidence: The text containing the evidence, assured to be in the default language.
        :param question: The question to answer, assured to be in the default language.
        :param lang: Optional language code.
        :return: The passage from the evidence that best answers the question.
        """
        raise NotImplementedError

    # user facing methods
    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["evidence", "question"])
    @auto_translate(translate_keys=["evidence", "question"])
    def extract_answer(self, evidence: str, question: str,
                       lang: Optional[str] = None) -> str:
        """
        Extract the best passage from evidence that answers the question with automatic translation and caching if needed.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "evidence" and "question" are automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param evidence: The text containing the evidence.
        :param question: The question to answer.
        :param lang: Optional language code.
        :return: The passage from the evidence that answers the question.
        """
        # extract answer from doc
        return self.get_best_passage(evidence, question, lang=lang)


class MultipleChoiceSolver(AbstractSolver):
    """
    Solver for selecting the best answer from a question with multiple choices,
    handling automatic translation as needed.
    """

    @abc.abstractmethod
    def rerank(self, query: str, options: List[str],
               lang: Optional[str] = None,
               return_index: bool = False) -> List[Tuple[float, Union[str, int]]]:
        """
        Rank the provided options based on the query.

        :param query: The query text, assured to be in the default language.
        :param options: A list of answer options, each assured to be in the default language.
        :param lang: Optional language code.
        :param return_index: If True, return the index of the best option; otherwise, return the best option text.
        :return: A list of tuples where each tuple contains a score and the corresponding option text, sorted by score.
        """
        raise NotImplementedError

    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["query", "options"])
    @auto_translate(translate_keys=["query", "options"])
    def select_answer(self, query: str, options: List[str],
                      lang: Optional[str] = None,
                      return_index: bool = False) -> Union[str, int]:
        """
        Select the best answer from the provided options based on the query with automatic translation and caching if needed.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query" and "options"  are automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param query: The query text.
        :param options: A list of answer options.
        :param lang: Optional language code.
        :param return_index: If True, return the index of the best option; otherwise, return the best option text.
        :return: The best answer from the options list, or the index of the best option if `return_index` is True.
        """
        return self.rerank(query, options, lang=lang, return_index=return_index)[0][1]


class EntailmentSolver(AbstractSolver):
    """ select best answer from question + multiple choice
    handling automatic translation back and forth as needed"""

    @abc.abstractmethod
    def check_entailment(self, premise: str, hypothesis: str,
                         lang: Optional[str] = None) -> bool:
        """
        Check if the premise entails the hypothesis.

        :param premise: The premise text, assured to be in the default language.
        :param hypothesis: The hypothesis text, assured to be in the default language.
        :param lang: Optional language code.
        :return: True if the premise entails the hypothesis; False otherwise.
        """
        raise NotImplementedError

    # user facing methods
    @_deprecate_context2lang()
    @auto_detect_lang(text_keys=["premise", "hypothesis"])
    @auto_translate(translate_keys=["premise", "hypothesis"])
    def entails(self, premise: str, hypothesis: str, lang: Optional[str] = None) -> bool:
        """
        Determine if the premise entails the hypothesis with automatic translation and caching if needed.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "premise" and "hypothesis" are automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param premise: The premise text.
        :param hypothesis: The hypothesis text.
        :param lang: Optional language code.
        :return: True if the premise entails the hypothesis; False otherwise.
        """
        # check for entailment
        return self.check_entailment(premise, hypothesis, lang=lang)


def _do_tx(solver, data: Any, source_lang: str, target_lang: str) -> Any:
    """
    Translate the given data from source language to target language using the provided solver.

    Args:
        solver: The translation solver.
        data (Any): The data to translate. Can be a string, list, dictionary, or tuple.
        source_lang (str): The source language code.
        target_lang (str): The target language code.

    Returns:
        Any: The translated data in the same structure as the input data.
    """
    if isinstance(data, str):
        return solver.translate(data,
                                source_lang=source_lang, target_lang=target_lang)
    elif isinstance(data, list):
        for idx, e in enumerate(data):
            data[idx] = _do_tx(solver, e, source_lang=source_lang, target_lang=target_lang)
    elif isinstance(data, dict):
        for k, v in data.items():
            data[k] = _do_tx(solver, v, source_lang=source_lang, target_lang=target_lang)
    elif isinstance(data, tuple) and len(data) == 2:
        if isinstance(data[0], str):
            a = _do_tx(solver, data[0], source_lang=source_lang, target_lang=target_lang)
        else:
            a = data[0]
        if isinstance(data[1], str):
            b = _do_tx(solver, data[1], source_lang=source_lang, target_lang=target_lang)
        else:
            b = data[1]
        return (a, b)
    return data


def _call_with_sanitized_kwargs(func, *args: Any,
                                lang: Optional[str] = None,
                                units: Optional[str] = None) -> Any:
    """
    Call a function with sanitized keyword arguments for language and units.

    Args:
        func: The function to call.
        args (Any): Positional arguments to pass to the function.
        lang (Optional[str]): Optional language code. Defaults to None.
        units (Optional[str]): Optional units for the query. Defaults to None.

    Returns:
        Any: The result of the function call.
    """
    params = inspect.signature(func).parameters
    kwargs = {}

    # ensure context is passed, it didn't used to be optional
    if "context" in params and "context" not in kwargs:
        kwargs["context"] = {}

    if "lang" in params:
        # new style - only lang/units is passed
        kwargs["lang"] = lang
    elif "context" in kwargs:
        # old style - when plugins received context only
        kwargs["context"]["lang"] = lang

    if "units" in params:
        # new style - only lang/units is passed
        kwargs["units"] = units
    elif "context" in kwargs:
        # old style - when plugins received context only
        kwargs["context"]["units"] = units

    return func(*args, **kwargs)
