from json_database import JsonStorageXDG
from ovos_utils.xdg_utils import xdg_cache_home
from quebra_frases import sentence_tokenize
from ovos_utils.log import LOG
from ovos_plugin_manager.language import OVOSLangTranslationFactory


class AbstractSolver:
    # these are defined by the plugin developer
    priority = 50
    enable_tx = False
    enable_cache = False

    def __init__(self, config=None, *args, **kwargs):
        if args or kwargs:
            LOG.warning("solver plugins init signature changed, please update to accept a single config kwarg. "
                        "an exception will be raised in next stable release")
            for arg in args:
                if isinstance(arg, str):
                    kwargs["name"] = arg
                if isinstance(arg, int):
                    kwargs["priority"] = arg
            if "priority" in kwargs:
                self.priority = kwargs["priority"]
            if "enable_tx" in kwargs:
                self.enable_tx = kwargs["enable_tx"]
            if "enable_cache" in kwargs:
                self.enable_cache = kwargs["enable_cache"]
        self.config = config or {}
        self.supported_langs = self.config.get("supported_langs") or []
        self.default_lang = self.config.get("lang", "en")
        if self.default_lang not in self.supported_langs:
            self.supported_langs.insert(0, self.default_lang)
        self.translator = OVOSLangTranslationFactory.create()

    @staticmethod
    def sentence_split(text, max_sentences=25):
        return sentence_tokenize(text)[:max_sentences]

    def _get_user_lang(self, context, lang=None):
        context = context or {}
        lang = lang or context.get("lang") or self.default_lang
        lang = lang.split("-")[0]
        return lang

    def _tx_query(self, query, context=None, lang=None):
        if not self.enable_tx:
            return query, context, lang
        context = context or {}
        lang = user_lang = self._get_user_lang(context, lang)

        # translate input to default lang
        if user_lang not in self.supported_langs:
            lang = self.default_lang
            query = self.translator.translate(query, lang, user_lang)

        context["lang"] = lang

        # HACK - cleanup some common translation mess ups
        # this is properly solving by using a good translate plugin
        # only common mistakes in default libretranslate plugin are handled
        if lang.startswith("en"):
            query = query.replace("who is is ", "who is ")

        return query, context, lang

    def shutdown(self):
        """ module specific shutdown method """
        pass


class QuestionSolver(AbstractSolver):
    """free form unscontrained spoken question solver
    handling automatic translation back and forth as needed"""

    def __init__(self, config=None, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        name = kwargs.get("name") or self.__class__.__name__
        if self.enable_cache:
            # cache contains raw data
            self.cache = JsonStorageXDG(name + "_data",
                                        xdg_folder=xdg_cache_home(),
                                        subfolder="neon_solvers")
            # spoken cache contains dialogs
            self.spoken_cache = JsonStorageXDG(name,
                                               xdg_folder=xdg_cache_home(),
                                               subfolder="neon_solvers")
        else:
            self.cache = self.spoken_cache = {}

    # plugin methods to override
    def get_spoken_answer(self, query, context):
        """
        query assured to be in self.default_lang
        return a single sentence text response
        """
        raise NotImplementedError

    def get_data(self, query, context):
        """
        query assured to be in self.default_lang
        return a dict response
        """
        raise NotImplementedError

    def get_image(self, query, context=None):
        """
        query assured to be in self.default_lang
        return path/url to a single image to acompany spoken_answer
        """
        raise NotImplementedError

    def get_expanded_answer(self, query, context=None):
        """
        query assured to be in self.default_lang
        return a list of ordered steps to expand the answer, eg, "tell me more"
        {
            "title": "optional",
            "summary": "speak this",
            "img": "optional/path/or/url
        }
        :return:
        """
        raise NotImplementedError

    # user facing methods
    def search(self, query, context=None, lang=None):
        """
        cache and auto translate query if needed
        returns translated response from self.get_data
        """
        user_lang = self._get_user_lang(context, lang)
        query, context, lang = self._tx_query(query, context, lang)
        # read from cache
        if self.enable_cache and query in self.cache:
            data = self.cache[query]
        else:
            # search data
            try:
                data = self.get_data(query, context)
            except:
                return {}

        # save to cache
        if self.enable_cache:
            self.cache[query] = data
            self.cache.store()

        # translate english output to user lang
        if self.enable_tx and user_lang not in self.supported_langs:
            return self.translator.translate_dict(data, user_lang, lang)
        return data

    def visual_answer(self, query, context=None, lang=None):
        """
        cache and auto translate query if needed
        returns image that answers query
        """
        query, context, lang = self._tx_query(query, context, lang)
        return self.get_image(query, context)

    def spoken_answer(self, query, context=None, lang=None):
        """
        cache and auto translate query if needed
        returns chunked and translated response from self.get_spoken_answer
        """
        user_lang = self._get_user_lang(context, lang)
        query, context, lang = self._tx_query(query, context, lang)

        # get answer
        if self.enable_cache and query in self.spoken_cache:
            # read from cache
            summary = self.spoken_cache[query]
        else:
            summary = self.get_spoken_answer(query, context)
            # save to cache
            if self.enable_cache:
                self.spoken_cache[query] = summary
                self.spoken_cache.store()

        # summarize
        if summary:
            # translate english output to user lang
            if self.enable_tx and user_lang not in self.supported_langs:
                return self.translator.translate(summary, user_lang, lang)
            else:
                return summary

    def long_answer(self, query, context=None, lang=None):
        """
        return a list of ordered steps to expand the answer, eg, "tell me more"
        step0 is always self.spoken_answer and self.get_image
        {
            "title": "optional",
            "summary": "speak this",
            "img": "optional/path/or/url
        }
        :return:
        """
        user_lang = self._get_user_lang(context, lang)
        query, context, lang = self._tx_query(query, context, lang)
        steps = self.get_expanded_answer(query, context)

        # use spoken_answer as last resort
        if not steps:
            summary = self.get_spoken_answer(query, context)
            if summary:
                img = self.get_image(query, context)
                steps = [{"title": query, "summary": step0, "img": img}
                         for step0 in self.sentence_split(summary, -1)]

        # translate english output to user lang
        if self.enable_tx and user_lang not in self.supported_langs:
            return self.translator.translate_list(steps, user_lang, lang)
        return steps


class TldrSolver(AbstractSolver):
    """perform NLP summarization task,
    handling automatic translation back and forth as needed"""

    # plugin methods to override
    def get_tldr(self, document, context):
        """
        document assured to be in self.default_lang
         returns summary of provided document
        """
        raise NotImplementedError

    # user facing methods
    def tldr(self, document, context=None, lang=None):
        """
        cache and auto translate query if needed
        returns summary of provided document
        """
        user_lang = self._get_user_lang(context, lang)
        document, context, lang = self._tx_query(document, context, lang)

        # summarize
        tldr = self.get_tldr(document, context)

        # translate output to user lang
        if self.enable_tx and user_lang not in self.supported_langs:
            return self.translator.translate(tldr, user_lang, lang)
        return tldr


class EvidenceSolver(AbstractSolver):
    """perform NLP reading comprehension task,
    handling automatic translation back and forth as needed"""

    # plugin methods to override
    def get_best_passage(self, evidence, question, context):
        """
        evidence and question assured to be in self.default_lang
         returns summary of provided document
        """
        raise NotImplementedError

    # user facing methods
    def extract_answer(self, evidence, question, context=None, lang=None):
        """
        cache and auto translate evidence and question if needed
        returns passage from evidence that answers question
        """
        user_lang = self._get_user_lang(context, lang)
        evidence, context, lang = self._tx_query(evidence, context, lang)
        question, context, lang = self._tx_query(question, context, lang)

        # extract answer from doc
        ans = self.get_best_passage(evidence, question, context)

        # translate output to user lang
        if self.enable_tx and user_lang not in self.supported_langs:
            return self.translator.translate(ans, user_lang, lang)
        return ans


class MultipleChoiceSolver(AbstractSolver):
    """ select best answer from question + multiple choice
    handling automatic translation back and forth as needed"""

    # plugin methods to override
    def select_answer(self, query, options, context):
        """
        query and options assured to be in self.default_lang
        return best answer from options list
        """
        raise NotImplementedError

    # user facing methods
    def solve(self, query, options, context=None, lang=None):
        """
        cache and auto translate query and options if needed
        returns best answer from provided options
        """
        user_lang = self._get_user_lang(context, lang)
        query, context, lang = self._tx_query(query, context, lang)
        opts = [self.translator.translate(opt, lang, user_lang)
                for opt in options]

        # select best answer
        ans = self.select_answer(query, opts, context)

        idx = opts.index(ans)
        return options[idx]


class EntailmentSolver(AbstractSolver):
    """ select best answer from question + multiple choice
    handling automatic translation back and forth as needed"""

    # plugin methods to override
    def check_entailment(self, premise, hypothesis, context):
        """
        premise and hyopithesis assured to be in self.default_lang
        return Bool, True if premise entails the hypothesis False otherwise
        """
        raise NotImplementedError

    # user facing methods
    def entails(self, premise, hypothesis, context=None, lang=None):
        """
        cache and auto translate premise and hypothesis if needed
        return Bool, True if premise entails the hypothesis False otherwise
        """
        user_lang = self._get_user_lang(context, lang)
        query, context, lang = self._tx_query(query, context, lang)

        # summarize
        return self.check_entailment(premise, hypothesis)
