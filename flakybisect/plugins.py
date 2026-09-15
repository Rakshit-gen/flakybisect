"""Registries for the swappable pieces: classifiers and reporters.

Built-in implementations register themselves on import (see classify.py,
reporters.py). To add your own, register before building the graph:

    from flakybisect.plugins import register_classifier

    @register_classifier("my-classifier")
    def my_classifier(reruns, bisect):
        return "some label"

Then pass --classifier my-classifier on the CLI, or classifier="my-classifier"
to build_graph().
"""
from __future__ import annotations

from typing import Callable

CLASSIFIERS: dict[str, Callable] = {}
REPORTERS: dict[str, Callable] = {}


def register_classifier(name: str):
    def deco(fn: Callable) -> Callable:
        CLASSIFIERS[name] = fn
        return fn

    return deco


def register_reporter(name: str):
    def deco(fn: Callable) -> Callable:
        REPORTERS[name] = fn
        return fn

    return deco
