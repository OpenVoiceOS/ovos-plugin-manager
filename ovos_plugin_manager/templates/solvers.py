# Original AbstractSolver class taken from: https://github.com/Neongeckocom/neon_solvers, licensed under BSD-3
# QuestionSolver Improvements and other solver classes are OVOS originals licensed under Apache 2.0

import abc
import inspect
from functools import wraps, lru_cache
from typing import Optional, List, Iterable, Tuple, Dict, Union

from json_database import JsonStorageXDG
from ovos_utils import flatten_list
from ovos_utils.log import LOG, log_deprecation
from ovos_utils.xdg_utils import xdg_cache_home
from quebra_frases import sentence_tokenize

from ovos_plugin_manager.language import OVOSLangTranslationFactory, OVOSLangDetectionFactory
from ovos_plugin_manager.templates.language import LanguageTranslator, LanguageDetector


def _deprecate_context2lang():
    """Decorator to deprecate the 'context' kwarg and replace it with 'lang'.
    NOTE: can only be used in methods that accept both "lang" and "context" as arguments"""

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
                                "please pass 'lang' as it's own kwarg instead", "0.1.0")
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


def auto_translate(translate_keys: List[str]):
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

            # detect language if needed
            lang = kwargs.get("lang")
            if lang is None:
                for k in translate_keys:
                    v = kwargs.get(k)
                    if isinstance(v, str):
                        lang = solver.detect_language(v)
                        break

            # check if translation can be skipped
            if any([lang is None,
                    lang == solver.default_lang,
                    lang in solver.supported_langs]):
                return func(*args, **kwargs)

            # translate input keys
            for k in translate_keys:
                v = kwargs.get(k)
                if isinstance(v, str):
                    if v.startswith("http"):
                        continue
                    kwargs[k] = solver.translate(v,
                                                 source_lang=lang,
                                                 target_lang=solver.default_lang)
                elif isinstance(v, list):
                    kwargs[k] = solver.translate_list(v,
                                                      source_lang=lang,
                                                      target_lang=solver.default_lang)
                elif isinstance(v, dict):
                    kwargs[k] = solver.translate_dict(v,
                                                      source_lang=lang,
                                                      target_lang=solver.default_lang)

            output = func(*args, **kwargs)

            # reverse translate
            if isinstance(output, str):
                return solver.translate(output,
                                        source_lang=solver.default_lang,
                                        target_lang=lang)
            elif isinstance(output, list):
                return solver.translate_list(output,
                                             source_lang=solver.default_lang,
                                             target_lang=lang)
            elif isinstance(output, dict):
                return solver.translate_dict(output,
                                             source_lang=solver.default_lang,
                                             target_lang=lang)
            return output

        return func_wrapper

    return func_decorator


def _call_with_sanitized_kwargs(func, *args, lang: Optional[str] = None):
    # Inspect the function signature to ensure it has both 'lang' and 'context' parameters
    params = inspect.signature(func).parameters
    kwargs = {}
    if "lang" in params:
        # new style - only lang is passed
        kwargs["lang"] = lang
    elif "context" in kwargs:
        # old style - when plugins received context only
        kwargs["context"]["lang"] = lang
    return func(*args, **kwargs)


class AbstractSolver:
    """Base class for solvers that perform various NLP tasks."""

    def __init__(self, config=None,
                 translator: Optional[LanguageTranslator] = None,
                 detector: Optional[LanguageDetector] = None,
                 priority=50,
                 enable_tx=False,
                 enable_cache=False,
                 *args, **kwargs):
        self.priority = priority
        self.enable_tx = enable_tx
        self.enable_cache = enable_cache
        self.config = config or {}
        self.supported_langs = self.config.get("supported_langs") or []
        self.default_lang = self.config.get("lang", "en")
        if self.default_lang not in self.supported_langs:
            self.supported_langs.insert(0, self.default_lang)
        self.translator = translator or OVOSLangTranslationFactory.create()
        self.detector = detector or OVOSLangDetectionFactory.create()
        LOG.debug(f"{self.__class__.__name__} default language: {self.default_lang}")

    @staticmethod
    def sentence_split(text: str, max_sentences: int = 25) -> List[str]:
        """
        Split text into sentences.

        :param text: Input text.
        :param max_sentences: Maximum number of sentences to return.
        :return: List of sentences.
        """
        try:
            # sentence_tokenize occasionally has issues with \n for some reason
            return flatten_list([sentence_tokenize(t)
                                 for t in text.split("\n")])[:max_sentences]
        except Exception as e:
            LOG.exception(f"Error in sentence_split: {e}")
            return [text]

    @lru_cache(maxsize=128)
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text.

        :param text: Input text.
        :return: Detected language code.
        """
        return self.detector.detect(text)

    @lru_cache(maxsize=128)
    def translate(self, text: str,
                  target_lang: Optional[str] = None,
                  source_lang: Optional[str] = None) -> str:
        """
        Translate text from source_lang to target_lang.

        :param text: Input text.
        :param target_lang: Target language code.
        :param source_lang: Source language code.
        :return: Translated text.
        """
        source_lang = source_lang or self.detect_language(text)
        target_lang = target_lang or self.default_lang
        if source_lang.split("-")[0] == target_lang.split("-")[0]:
            return text  # skip translation
        return self.translator.translate(text,
                                         target=target_lang,
                                         source=source_lang)

    def translate_list(self, data: List[str],
                       target_lang: Optional[str] = None,
                       source_lang: Optional[str] = None) -> List[str]:
        """
        Translate a list of strings from source_lang to target_lang.

        :param data: List of strings.
        :param target_lang: Target language code.
        :param source_lang: Source language code.
        :return: List of translated strings.
        """
        return self.translator.translate_list(data,
                                              lang_tgt=target_lang,
                                              lang_src=source_lang)

    def translate_dict(self, data: Dict[str, str],
                       target_lang: Optional[str] = None,
                       source_lang: Optional[str] = None) -> Dict[str, str]:
        """
        Translate a dictionary of strings from source_lang to target_lang.

        :param data: Dictionary of strings.
        :param target_lang: Target language code.
        :param source_lang: Source language code.
        :return: Dictionary of translated strings.
        """
        return self.translator.translate_dict(data,
                                              lang_tgt=target_lang,
                                              lang_src=source_lang)

    def shutdown(self):
        """Module specific shutdown method."""
        pass


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
                 *args, **kwargs):
        """
        Initialize the QuestionSolver.

        :param config: Optional configuration dictionary.
        :param translator: Optional language translator.
        :param detector: Optional language detector.
        :param priority: Priority of the solver.
        :param enable_tx: Flag to enable translation.
        :param enable_cache: Flag to enable caching.
        """
        super().__init__(config, translator, detector,
                         priority, enable_tx, enable_cache,
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
    def get_spoken_answer(self, query: str, lang: Optional[str] = None) -> str:
        """
        Obtain the spoken answer for a given query.

        :param query: The query text.
        :param lang: Optional language code.
        :return: The spoken answer as a text response.
        """
        raise NotImplementedError

    @_deprecate_context2lang()
    def stream_utterances(self, query: str, lang: Optional[str] = None) -> Iterable[str]:
        """
        Stream utterances for the given query as they become available.

        :param query: The query text.
        :param lang: Optional language code.
        :return: An iterable of utterances.
        """
        ans = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang)
        for utt in self.sentence_split(ans):
            yield utt

    @_deprecate_context2lang()
    def get_data(self, query: str, lang: Optional[str] = None) -> Optional[dict]:
        """
        Retrieve data for the given query.

        :param query: The query text.
        :param lang: Optional language code.
        :return: A dictionary containing the answer.
        """
        return {"answer": _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang)}

    @_deprecate_context2lang()
    def get_image(self, query: str, lang: Optional[str] = None) -> Optional[str]:
        """
        Get the path or URL to an image associated with the query.

        :param query: The query text
        :param lang: Optional language code.
        :return: The path or URL to a single image.
        """
        return None

    @_deprecate_context2lang()
    def get_expanded_answer(self, query: str, lang: Optional[str] = None) -> List[dict]:
        """
        Get an expanded list of steps to elaborate on the answer.

        :param query: The query text
        :param lang: Optional language code.
        :return: A list of dictionaries with each step containing a title, summary, and optional image.
        """
        return [{"title": query,
                 "summary": _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang),
                 "img": _call_with_sanitized_kwargs(self.get_image, query, lang=lang)}]

    # user facing methods
    @_deprecate_context2lang()
    @auto_translate(translate_keys=["query"])
    def search(self, query: str, lang: Optional[str] = None) -> dict:
        """
        Perform a search with automatic translation and caching.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param query: The query text.
        :param lang: Optional language code.
        :return: The data dictionary retrieved from the cache or computed anew.
        """
        # read from cache
        if self.enable_cache and query in self.cache:
            data = self.cache[query]
        else:
            # search data
            try:
                data = _call_with_sanitized_kwargs(self.get_data, query, lang=lang)
            except:
                return {}

        # save to cache
        if self.enable_cache:
            self.cache[query] = data
            self.cache.store()
        return data

    @_deprecate_context2lang()
    @auto_translate(translate_keys=["query"])
    def visual_answer(self, query: str, lang: Optional[str] = None) -> str:
        """
        Retrieve the image associated with the query with automatic translation and caching.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param query: The query text.
        :param lang: Optional language code.
        :return: The path or URL to the image.
        """
        return _call_with_sanitized_kwargs(self.get_image, query, lang=lang)

    @_deprecate_context2lang()
    @auto_translate(translate_keys=["query"])
    def spoken_answer(self, query: str, lang: Optional[str] = None) -> str:
        """
        Retrieve the spoken answer for the query with automatic translation and caching.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param query: The query text.
        :param lang: Optional language code.
        :return: The spoken answer as a text response.
        """
        # get answer
        if self.enable_cache and query in self.spoken_cache:
            # read from cache
            summary = self.spoken_cache[query]
        else:

            summary = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang)
            # save to cache
            if self.enable_cache:
                self.spoken_cache[query] = summary
                self.spoken_cache.store()
        return summary

    @_deprecate_context2lang()
    @auto_translate(translate_keys=["query"])
    def long_answer(self, query: str, lang: Optional[str] = None) -> List[dict]:
        """
        Retrieve a detailed list of steps to expand the answer.

        NOTE: "lang" assured to be in self.supported_langs,
            otherwise "query"  automatically translated to self.default_lang.
            If translations happens, the returned value of this method will also
            be automatically translated back

        :param query: The query text.
        :param lang: Optional language code.
        :return: A list of steps to elaborate on the answer, with each step containing a title, summary, and optional image.
        """
        steps = _call_with_sanitized_kwargs(self.get_expanded_answer, query, lang=lang)
        # use spoken_answer as last resort
        if not steps:
            summary = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang)
            if summary:
                img = _call_with_sanitized_kwargs(self.get_image, query, lang=lang)
                steps = [{"title": query, "summary": step0, "img": img}
                         for step0 in self.sentence_split(summary, -1)]
        return steps


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

    # plugin methods to override

    # TODO  - make abstract in the future,
    #  just giving some time buffer to update existing
    #  plugins in the wild missing this method
    # @abc.abstractmethod
    def rerank(self, query: str, options: List[str],
               lang: Optional[str] = None) -> List[Tuple[float, str]]:
        """
        Rank the provided options based on the query.

        :param query: The query text, assured to be in the default language.
        :param options: A list of answer options, each assured to be in the default language.
        :param lang: Optional language code.
        :return: A list of tuples where each tuple contains a score and the corresponding option text, sorted by score.
        """
        raise NotImplementedError

    @_deprecate_context2lang()
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
        best = self.rerank(query, options, lang=lang)[0][1]
        if return_index:
            return options.index(best)
        return best


class EntailmentSolver(AbstractSolver):
    """ select best answer from question + multiple choice
    handling automatic translation back and forth as needed"""

    # plugin methods to override

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
    @auto_translate(translate_keys=["premise", "hypothesis"])
    def entails(self, premise: str, hypothesis: str,
                lang: Optional[str] = None) -> bool:
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
