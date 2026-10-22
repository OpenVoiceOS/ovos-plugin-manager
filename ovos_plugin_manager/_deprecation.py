import inspect


def imported_internally(module_name: str) -> bool:
    """Whether this import was triggered by ovos_plugin_manager wiring itself
    together rather than by an external caller.

    A module-level deprecation notice is a message to external callers. When
    one deprecated module imports another to assemble the package, firing that
    notice only produces log noise whose origin is the library itself, so the
    internal case is detected here and the notice is skipped for it.
    """
    for frame_info in inspect.stack()[1:]:
        name = frame_info.frame.f_globals.get("__name__", "")
        if name == module_name or name.startswith("importlib"):
            continue
        return name.startswith("ovos_plugin_manager")
    return False
