import json

from ovos_utils.log import LOG

from ovos_plugin_manager.stt import get_stt_lang_configs
from ovos_plugin_manager.tts import get_tts_lang_configs


def hash_dict(d):
    return str(hash(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=True)))


class PluginUIHelper:
    """ Helper class to provide metadata for UI consumption
    This allows all sorts of rich integrations by
    any downstream application wanting to provide a plugin store

    This is the central place to manage anything UI related,
    downstream should not need to import anything else
    """
    _stt_opts = {}
    _tts_opts = {}

    @classmethod
    def stt_option2config(cls, opt):
        """ get the equivalent plugin config from a UI display model """
        return cls._stt_opts.get(hash_dict(opt))

    @classmethod
    def stt_config2option(cls, cfg, lang=None):
        """ get the equivalent UI display model from a plugin config """
        engine = cfg["module"]
        lang = lang or cfg.get("lang")
        plugin_display_name = engine.replace("_", " ").replace("-", " ").title()
        opt = {"plugin_name": plugin_display_name,
               "display_name": cfg.get("display_name", " "),
               "offline": cfg.get("offline", False),
               "lang": lang,
               "engine": engine}
        cls._stt_opts[hash_dict(opt)] = cfg
        return opt

    @classmethod
    def get_stt_display_options(cls, lang, blacklist=None, preferred=None, max_opts=20):
        # NOTE: mycroft-gui will crash if theres more than 20 options according to @aiix
        try:
            blacklist = blacklist or []
            stt_opts = []
            cfgs = get_stt_lang_configs(lang=lang, include_dialects=True)
            for engine, configs in cfgs.items():
                if engine in blacklist:
                    continue
                for config in configs:
                    d = cls.stt_config2option(config, lang)
                    if preferred and preferred not in blacklist and preferred == engine:
                        # Sort the list for UI to display the preferred STT engine first
                        # allow images to set a preferred engine
                        stt_opts.insert(0, d)
                    else:
                        stt_opts.append(d)
            return stt_opts[:max_opts]
        except Exception as e:
            LOG.error(e)
            # Return an empty list if there is an error
            # UI will handle this and display an error message
            return []

    @classmethod
    def tts_option2config(cls, opt):
        """ get the equivalent plugin config from a UI display model"""
        return cls._tts_opts.get(hash_dict(opt))

    @classmethod
    def tts_config2option(cls, cfg, lang=None):
        """ get the equivalent UI display model from a tts plugin config"""
        engine = cfg["module"]
        lang = lang or cfg.get("lang")
        plugin_display_name = engine.replace("_", " ").replace("-", " ").title()
        opt = {"plugin_name": plugin_display_name,
               "display_name": cfg.get("display_name", " "),
               "gender": cfg.get("gender", " "),
               "offline": cfg.get("offline", False),
               "lang": lang,
               "engine": engine}
        cls._tts_opts[hash_dict(opt)] = cfg
        return opt

    @classmethod
    def get_tts_display_options(cls, lang, blacklist=None, preferred=None, max_opts=20):
        # NOTE: mycroft-gui will crash if theres more than 20 options according to @aiix
        try:
            blacklist = blacklist or []
            tts_opts = []
            cfgs = get_tts_lang_configs(lang=lang, include_dialects=True)
            for engine, configs in cfgs.items():
                if engine in blacklist:
                    continue
                for voice in configs:
                    d = cls.tts_config2option(voice, lang)
                    if preferred and preferred not in blacklist and preferred == engine:
                        # Sort the list for UI to display the preferred TTS engine first
                        # allow images to set a preferred engine
                        tts_opts.insert(0, d)
                    else:
                        tts_opts.append(d)
            return tts_opts[:max_opts]
        except Exception as e:
            LOG.error(e)
            # Return an empty list if there is an error
            # UI will handle this and display an error message
            return []
