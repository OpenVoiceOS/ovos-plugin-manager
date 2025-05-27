import abc
import inspect
from functools import wraps
from typing import Optional, List, Iterable, Tuple, Dict, Union, Any

from json_database import JsonStorageXDG
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG, log_deprecation
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
    """
    Decorator that automatically detects and injects the language code into the "lang" argument if it is missing.
    
    If "lang" is not provided, attempts language detection on specified keyword arguments or, if unsuccessful, on positional string arguments containing multiple words. The detected language is standardized and passed to the decorated function.
    """

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
                        try:
                            lang = solver.detect_language(v)
                            LOG.debug(f"detected 'lang': {lang} in key: '{k}' for func: {func}")
                        except Exception as e:
                            LOG.error(f"failed to detect 'lang': {e}")
                            continue
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
                          Returns a spoken answer string for the given query.
                          
                          Args:
                              query: The input query to answer.
                              lang: Optional language code for the answer.
                              units: Optional units relevant to the query.
                          
                          Returns:
                              The spoken answer as a string, or None if not implemented.
                          """
        raise NotImplementedError

    def stream_utterances(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None) -> Iterable[str]:
        """
                          Yields sentence-split utterances from the spoken answer to a query.
                          
                          Args:
                              query: The input query text.
                              lang: Optional language code.
                              units: Optional units for the query.
                          
                          Yields:
                              Individual utterances as strings, split from the spoken answer.
                          """
        ans = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)
        for utt in self.sentence_split(ans):
            yield utt

    def get_data(self, query: str,
                 lang: Optional[str] = None,
                 units: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
                 Returns a dictionary containing the spoken answer for the given query.
                 
                 The answer is provided under the "answer" key. Language and units can be specified to control the response.
                 """
        return {"answer": _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)}

    def get_image(self, query: str,
                  lang: Optional[str] = None,
                  units: Optional[str] = None) -> Optional[str]:
        """
                  Returns the path or URL to an image associated with the query, or None if not available.
                  
                  This method is intended to be overridden by subclasses to provide relevant images for a given query.
                  """
        return None

    def get_expanded_answer(self, query: str,
                            lang: Optional[str] = None,
                            units: Optional[str] = None) -> List[Dict[str, str]]:
        """
                            Returns a list containing an expanded answer with title, summary, and image.
                            
                            The returned list contains a single dictionary with the original query as the title, the spoken answer as the summary, and an image (if available).
                            """
        return [{"title": query,
                 "summary": _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units),
                 "img": _call_with_sanitized_kwargs(self.get_image, query, lang=lang, units=units)}]

    # user facing methods
    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def search(self, query: str,
               lang: Optional[str] = None,
               units: Optional[str] = None) -> Optional[Dict]:
        """
               Performs a search for the given query, handling translation and caching as needed.
               
               If the query result is cached, returns the cached data. Otherwise, computes the result, optionally translating the query and response based on the specified or detected language. The result is cached for future use.
               
               Args:
                   query: The query text to search for.
                   lang: Optional language code. If not provided or unsupported, translation is applied.
                   units: Optional units relevant to the query.
               
               Returns:
                   A dictionary containing the search result data, or an empty dictionary if an error occurs.
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

    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def visual_answer(self, query: str,
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> Optional[str]:
        """
                      Returns the image path or URL associated with the query, with automatic language translation and caching.
                      
                      If the input language is not supported, the query is translated to the solver's default language before processing, and the result is translated back to the original language if necessary.
                      
                      Returns:
                          The image path or URL if available; otherwise, None.
                      """
        return _call_with_sanitized_kwargs(self.get_image, query, lang=lang, units=units)

    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def spoken_answer(self, query: str,
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> Optional[str]:
        """
                      Returns the spoken answer for a query, applying automatic translation and caching.
                      
                      If the input language is not supported, the query is translated to the default language before processing, and the answer is translated back to the original language if needed. Results may be cached for faster retrieval.
                      
                      Args:
                          query: The input query text.
                          lang: Optional language code for the query.
                          units: Optional units relevant to the query.
                      
                      Returns:
                          The spoken answer as a string, or None if unavailable.
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

    @auto_detect_lang(text_keys=["query"])
    @auto_translate(translate_keys=["query"])
    def long_answer(self, query: str,
                    lang: Optional[str] = None,
                    units: Optional[str] = None) -> List[Dict[str, str]]:
        """
                    Returns a detailed, step-by-step expanded answer for a given query.
                    
                    If no expanded answer is available, falls back to splitting the spoken answer into steps. Each step includes a title, summary, and optionally an image. Input and output are automatically translated as needed based on the specified or detected language.
                    
                    Args:
                        query: The input query to elaborate.
                        lang: Optional language code for translation.
                        units: Optional units relevant to the query.
                    
                    Returns:
                        A list of dictionaries, each representing a step with keys "title", "summary", and optionally "img".
                    """
        steps = _call_with_sanitized_kwargs(self.get_expanded_answer, query, lang=lang, units=units)
        # use spoken_answer as last resort
        if not steps:
            summary = _call_with_sanitized_kwargs(self.get_spoken_answer, query, lang=lang, units=units)
            if summary:
                img = _call_with_sanitized_kwargs(self.get_image, query, lang=lang, units=units)
                steps = [{"title": query, "summary": step, "img": img} for step in self.sentence_split(summary, -1)]
        return steps


class ChatMessageSolver(QuestionSolver):
    """A solver that processes chat history in LLM-style format to generate contextual responses.

    This class extends QuestionSolver to handle multi-turn conversations, maintaining
    context across messages. It expects chat messages in a format similar to LLM APIs:

     messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Knock knock."},
        {"role": "assistant", "content": "Who's there?"},
        {"role": "user", "content": "Orange."},
     ]
     """

    @abc.abstractmethod
    def continue_chat(self, messages: List[Dict[str, str]],
                      lang: Optional[str],
                      units: Optional[str] = None) -> Optional[str]:
        """Generate a response based on the chat history.

        Args:
            messages (List[Dict[str, str]]): List of chat messages, each containing 'role' and 'content'.
            lang (Optional[str]): The language code for the response. If None, will be auto-detected.
            units (Optional[str]): Optional unit system for numerical values.

        Returns:
            Optional[str]: The generated response or None if no response could be generated.
        """

    @auto_detect_lang(text_keys=["messages"])
    @auto_translate(translate_keys=["messages"])
    def get_chat_completion(self, messages: List[Dict[str, str]],
                            lang: Optional[str] = None,
                            units: Optional[str] = None) -> Optional[str]:
        return self.continue_chat(messages=messages, lang=lang, units=units)

    def stream_chat_utterances(self, messages: List[Dict[str, str]],
                               lang: Optional[str] = None,
                               units: Optional[str] = None) -> Iterable[str]:
        """
        Stream utterances for the given chat history as they become available.

        Args:
            messages: The chat messages.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            Iterable[str]: An iterable of utterances.
        """
        ans = _call_with_sanitized_kwargs(self.get_chat_completion, messages, lang=lang, units=units)
        for utt in self.sentence_split(ans):
            yield utt

    def get_spoken_answer(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None) -> Optional[str]:
        """Override of QuestionSolver.get_spoken_answer for API compatibility.

        This implementation converts the single query into a chat message format
        and delegates to continue_chat. While functional, direct use of chat-specific
        methods is recommended for chat-based interactions.
        """
        # just for api compat since it's a subclass, shouldn't be directly used
        return self.continue_chat(messages=[{"role": "user", "content": query}], lang=lang, units=units)


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
            # this log can be very spammy, only enable for debug during dev
            #LOG.debug(f"Rank {len(res) + 1} (score: {score}): {doc}")
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
                 Generates a summary of the provided document in the default language.
                 
                 Args:
                     document: The text to be summarized, guaranteed to be in the solver's default language.
                     lang: Optional language code for the summary.
                 
                 Returns:
                     A concise summary of the input document.
                 
                 Raises:
                     NotImplementedError: If the method is not implemented by a subclass.
                 """
        raise NotImplementedError

    # user facing methods
    @auto_detect_lang(text_keys=["document"])
    @auto_translate(translate_keys=["document"])
    def tldr(self, document: str, lang: Optional[str] = None) -> str:
        """
        Summarizes a document, automatically handling translation to and from the solver's default language if needed.
        
        If the input language is not supported, the document is translated to the default language before summarization, and the summary is translated back to the original language.
        
        Args:
            document: The text to summarize.
            lang: Optional language code for the summary.
        
        Returns:
            A summary of the provided document in the requested language.
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
                         Extracts the passage from the provided evidence that best answers the given question.
                         
                         Args:
                             evidence: Text containing the evidence in the default language.
                             question: Question to be answered, in the default language.
                             lang: Optional language code.
                         
                         Returns:
                             The passage from the evidence that most effectively answers the question.
                         """
        raise NotImplementedError

    # user facing methods
    @auto_detect_lang(text_keys=["evidence", "question"])
    @auto_translate(translate_keys=["evidence", "question"])
    def extract_answer(self, evidence: str, question: str,
                       lang: Optional[str] = None) -> str:
        """
                       Extracts the best passage from the provided evidence that answers the question, with automatic translation and optional caching.
                       
                       If the specified language is not supported, the evidence and question are translated to the default language before extraction, and the result is translated back to the original language.
                       
                       Args:
                           evidence: The text containing the evidence.
                           question: The question to answer.
                           lang: Optional language code.
                       
                       Returns:
                           The passage from the evidence that best answers the question.
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
               Ranks answer options by relevance to the query.
               
               Args:
                   query: The query text in the default language.
                   options: List of answer options in the default language.
                   lang: Optional language code for additional context.
                   return_index: If True, returns option indices instead of texts.
               
               Returns:
                   A list of (score, option) or (score, index) tuples, sorted by score descending.
               """
        raise NotImplementedError

    @auto_detect_lang(text_keys=["query", "options"])
    @auto_translate(translate_keys=["query", "options"])
    def select_answer(self, query: str, options: List[str],
                      lang: Optional[str] = None,
                      return_index: bool = False) -> Union[str, int]:
        """
                      Selects the best answer from a list of options for a given query, with automatic translation and optional index return.
                      
                      If the specified language is not supported, the query and options are translated to the default language before selection, and the result is translated back if necessary.
                      
                      Args:
                          query: The question or prompt to evaluate.
                          options: List of possible answer choices.
                          return_index: If True, returns the index of the best option; otherwise, returns the option text.
                      
                      Returns:
                          The best answer option or its index, depending on the value of return_index.
                      """
        return self.rerank(query, options, lang=lang, return_index=return_index)[0][1]


class EntailmentSolver(AbstractSolver):
    """ select best answer from question + multiple choice
    handling automatic translation back and forth as needed"""

    @abc.abstractmethod
    def check_entailment(self, premise: str, hypothesis: str,
                         lang: Optional[str] = None) -> bool:
        """
                         Determines whether a given premise entails a hypothesis.
                         
                         Args:
                             premise: The premise text in the default language.
                             hypothesis: The hypothesis text in the default language.
                             lang: Optional language code.
                         
                         Returns:
                             True if the premise entails the hypothesis; False otherwise.
                         """
        raise NotImplementedError

    # user facing methods
    @auto_detect_lang(text_keys=["premise", "hypothesis"])
    @auto_translate(translate_keys=["premise", "hypothesis"])
    def entails(self, premise: str, hypothesis: str, lang: Optional[str] = None) -> bool:
        """
        Determines whether the given premise entails the hypothesis, with automatic language translation if needed.
        
        If the provided language is not supported, the premise and hypothesis are translated to the default language before entailment checking. The result is returned as a boolean value.
        	
        Args:
        	premise: The premise text.
        	hypothesis: The hypothesis text.
        	lang: Optional language code.
        
        Returns:
        	True if the premise entails the hypothesis; False otherwise.
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
        try:
            return solver.translate(data,
                                    source_lang=source_lang, target_lang=target_lang)
        except Exception as e:
            LOG.error(f"Failed to translate '{data}' - ({e})")
            return data

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
