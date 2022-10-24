import json
from ovos_utils import flatten_list
from ovos_plugin_manager import PluginTypes
from ovos_plugin_manager.stt import get_stt_lang_configs
from ovos_plugin_manager.tts import get_tts_lang_configs


def hash_dict(d):
    return str(hash(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=True)))


class PluginUIHelper:
    """
    Helper class to provide metadata for UI consumption
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
               "engine": engine,
               "plugin_type": plugin_type}

        if plugin_type == PluginTypes.STT:
            if not cls._stt_opts and lang:
                # do initial scan
                cls.get_config_options(lang, PluginTypes.STT)
            cls._stt_opts[hash_dict(opt)] = cfg
        elif plugin_type == PluginTypes.TTS:
            if not cls._tts_opts and lang:
                # do initial scan
                cls.get_config_options(lang, PluginTypes.TTS)
            opt["gender"] = cfg["meta"].get("gender", "?")
            cls._tts_opts[hash_dict(opt)] = cfg
        else:
            raise NotImplementedError("only STT and TTS plugins are supported at this time")
        return opt

    @classmethod
    def option2config(cls, opt, plugin_type=None):
        """ get the equivalent plugin config from a UI display model """
        plugin_type = plugin_type or opt.get("plugin_type")
        if not plugin_type:
            raise ValueError("Unknown plugin type")
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
        for k in ["display_name", "gender", "offline", "priority"]:
            if k in cfg:
                meta[k] = cfg.pop(k)
        cfg["meta"] = meta
        return cfg

    @classmethod
    def get_config_options(cls, lang, plugin_type, blacklist=None, preferred=None,
                           max_opts=50, skip_setup=True, include_dialects=True):
        """ return a list of dicts with metadata for downstream UIs
        each option corresponds to a valid selectable plugin configuration, each plugin may report several options
        """
        # NOTE: mycroft-gui will crash if theres more than 20 options according to @aiix
        # TODO - validate that this is true and 20 is a real limit
        blacklist = blacklist or []
        opts = []
        preferred = preferred or []
        if isinstance(preferred, str):
            preferred = [preferred]
        if plugin_type == PluginTypes.STT:
            cfgs = get_stt_lang_configs(lang=lang, include_dialects=include_dialects)
        elif plugin_type == PluginTypes.TTS:
            cfgs = get_tts_lang_configs(lang=lang, include_dialects=include_dialects)
        else:
            raise NotImplementedError("only STT and TTS plugins are supported at this time")

        for engine, configs in cfgs.items():
            if engine in blacklist:
                continue
            pref_opts = []
            for config in configs:
                config = cls._migrate_old_cfg(config)
                if config["meta"].get("extra_setup"):
                    optional = config["meta"]["extra_setup"].get("optional")
                    if not optional and skip_setup:
                        # this config requires additional manual setup, skip was requested
                        continue
                config["module"] = engine  # this one should be ensured by get_lang_configs, but just in case
                d = cls.config2option(config, plugin_type, lang)
                if engine in preferred:
                    # Sort the list for UI to display the preferred STT engine first
                    # allow images to set a preferred engine
                    pref_opts.append(d)
                else:
                    opts.append(d)

            # artificially send preferred engine entries to start of list
            opts = pref_opts + opts
            return opts[:max_opts]

    @classmethod
    def get_plugin_options(cls, lang, plugin_type):
        """return a list of dicts with individual plugin metadata for UI display
        each entry contains metadata about the plugin and its own options
        """
        plugs = {}
        for entry in cls.get_config_options(lang, plugin_type):
            engine = entry["engine"]
            if engine not in plugs:
                plugs[engine] = {"engine": entry["engine"],
                                 "plugin_name": entry["plugin_name"],
                                 "supports_offline_mode": False,
                                 "supports_online_mode": False,
                                 "options": []}
                if plugin_type == PluginTypes.TTS:
                    plugs[engine]["supports_male_voice"] = False
                    plugs[engine]["supports_female_voice"] = False

            if "offline" in entry:
                if entry["offline"]:
                    plugs[engine]["supports_offline_mode"] = True
                else:
                    plugs[engine]["supports_online_mode"] = True

            if entry.get("gender", "?") == "male":
                plugs[engine]["supports_male_voice"] = True
            elif entry.get("gender", "?") == "female":
                plugs[engine]["supports_female_voice"] = True

            plugs[engine]["options"].append(entry)

        return flatten_list(plugs.values())

    @classmethod
    def get_extra_setup(cls, opt, plugin_type=None):
        """
        individual plugins can provide a equivalent structure to skills settingsmeta.json/yaml
        this can be used to display an extra step for plugin configuration,
        such as required api keys that cant be pre-included by plugins

        skills already define this data structure that allows exposing
        arbitrary configurations to downstream UIs,
        with selene being the reference consumer of that api
        """
        plugin_type = plugin_type or opt.get("plugin_type")
        if not plugin_type:
            raise ValueError("Unknown plugin type")
        meta = cls.option2config(opt, plugin_type)["meta"]
        return meta.get("extra_setup") or {}
