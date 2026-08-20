import mobase

from .plugin import OverwriteRegex


def createPlugin() -> mobase.IPlugin:
    return OverwriteRegex()
