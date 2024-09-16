# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from functools import lru_cache
from typing import Optional, List, Dict

from ovos_utils import flatten_list
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG
from quebra_frases import sentence_tokenize

from ovos_plugin_manager.language import OVOSLangTranslationFactory, OVOSLangDetectionFactory
from ovos_plugin_manager.templates.language import LanguageTranslator, LanguageDetector


class AbstractSolver:
    """Base class for solvers that perform various NLP tasks."""

    def __init__(self, config=None,
                 translator: Optional[LanguageTranslator] = None,
                 detector: Optional[LanguageDetector] = None,
                 priority=50,
                 enable_tx=False,
                 enable_cache=False,
                 internal_lang: Optional[str] = None,
                 *args, **kwargs):
        self.priority = priority
        self.enable_tx = enable_tx
        self.enable_cache = enable_cache
        self.config = config or {}
        self.supported_langs = self.config.get("supported_langs") or []
        self.default_lang = standardize_lang_tag(internal_lang or self.config.get("lang", "en"), macro=True)
        if self.default_lang not in self.supported_langs:
            self.supported_langs.insert(0, self.default_lang)
        self._translator = translator or OVOSLangTranslationFactory.create() if self.enable_tx else None
        self._detector = detector or OVOSLangDetectionFactory.create() if self.enable_tx else None
        LOG.debug(f"{self.__class__.__name__} default language: {self.default_lang}")

    @property
    def detector(self):
        """ language detector, lazy init on first access"""
        if not self._detector:
            # if it's being used, there is no recovery, do not try: except:
            self._detector = OVOSLangDetectionFactory.create()
        return self._detector

    @detector.setter
    def detector(self, val):
        self._detector = val

    @property
    def translator(self):
        """ language translator, lazy init on first access"""
        if not self._translator:
            # if it's being used, there is no recovery, do not try: except:
            self._translator = OVOSLangTranslationFactory.create()
        return self._translator

    @translator.setter
    def translator(self, val):
        self._translator = val

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
        source_lang = standardize_lang_tag(source_lang or self.detect_language(text), macro=True)
        target_lang = standardize_lang_tag(target_lang or self.default_lang, macro=True)
        if source_lang == target_lang:
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
