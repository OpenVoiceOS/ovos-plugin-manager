import json

from ovos_utils.log import LOG
from ovos_plugin_manager import PluginTypes
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
    def config2option(cls, cfg, plugin_type, lang=None):
        """ get the equivalent UI display model from a plugin config """
        cfg = cls._migrate_old_cfg(cfg)
        engine = cfg["module"]
        lang = lang or cfg.get("lang")

        plugin_display_name = engine.replace("_", " ").replace("-", " ").title()
        display_name = cfg["meta"].get("display_name", "?")
        offline = cfg["meta"].get("offline", True)  # TODO consider better handling of missing "offline" key

        opt = {"plugin_name": plugin_display_name,
               "display_name": display_name,
               "offline": offline,
               "lang": lang,
               "engine": engine}

        if plugin_type == PluginTypes.STT:
            cls._stt_opts[hash_dict(opt)] = cfg
        elif plugin_type == PluginTypes.TTS:
            opt["gender"] = cfg["meta"].get("gender", "?")
            cls._tts_opts[hash_dict(opt)] = cfg
        else:
            raise NotImplementedError("only STT and TTS plugins are supported at this time")
        return opt

    @classmethod
    def option2config(cls, opt, plugin_type):
        """ get the equivalent plugin config from a UI display model """
        if plugin_type == PluginTypes.STT:
            cfg = dict(cls._stt_opts.get(hash_dict(opt)))
        elif plugin_type == PluginTypes.TTS:
            cfg = dict(cls._tts_opts.get(hash_dict(opt)))
        else:
            raise NotImplementedError("only STT and TTS plugins are supported at this time")
        return cfg

    @staticmethod
    def _migrate_old_cfg(cfg):
        # TODO - until plugins are migrated to new "meta" subsection cleanup old keys
        meta = {}
        for k in ["display_name", "gender", "offline"]:
            if k in cfg:
                meta[k] = cfg.pop(k)
        cfg["meta"] = meta
        return cfg

    @classmethod
    def get_stt_display_options(cls, lang, blacklist=None, preferred=None, max_opts=20, skip_setup=True):
        # NOTE: mycroft-gui will crash if theres more than 20 options according to @aiix
        try:
            blacklist = blacklist or []
            stt_opts = []
            cfgs = get_stt_lang_configs(lang=lang, include_dialects=True)
            for engine, configs in cfgs.items():
                if engine in blacklist:
                    continue
                for config in configs:
                    config = cls._migrate_old_cfg(config)
                    if config.get("meta", {}).get("extra_setup") and skip_setup:
                        # this config requires additional manual setup, skip was requested
                        continue
                    config["module"] = engine  # this one should be ensurec by get_lang_configs, but just in case
                    d = cls.config2option(config, PluginTypes.STT, lang)
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
    def get_tts_display_options(cls, lang, blacklist=None, preferred=None, max_opts=20, skip_setup=True):
        # NOTE: mycroft-gui will crash if theres more than 20 options according to @aiix
        try:
            blacklist = blacklist or []
            tts_opts = []
            cfgs = get_tts_lang_configs(lang=lang, include_dialects=True)
            for engine, configs in cfgs.items():
                if engine in blacklist:
                    continue
                for config in configs:
                    config = cls._migrate_old_cfg(config)
                    config["module"] = engine  # this one should be ensured by get_lang_configs, but just in case
                    if config.get("meta", {}).get("extra_setup") and skip_setup:
                        # this config requires additional manual setup, skip was requested
                        continue
                    d = cls.config2option(config, PluginTypes.TTS, lang)
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

    @classmethod
    def get_extra_setup(cls, opt, plugin_type):
        """ this method is a placeholder and currently returns only a empty dict

        skills already define a settingsmeta.json/yaml structure
        that allows exposing arbitrary configurations to downstream UIs,
        with selene being the reference consumer of that api
        individual plugins should be able to provide a equivalent structure
        this can be used to display an extra step for plugin configuration,
        such as required api keys that cant be pre-included by plugins

        """
        meta = cls.option2config(opt, plugin_type)["meta"]
        return meta.get("extra_setup") or {}
