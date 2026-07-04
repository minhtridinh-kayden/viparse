"""Extraction engines: thin adapters wrapping maintained parse libraries.

Each engine matches the :class:`~viparse.protocols.Engine` Protocol and lazy-imports
its heavy dependency behind an extra, so importing this package never requires the
underlying library — only calling an engine does.
"""
