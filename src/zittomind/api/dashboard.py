"""Packaged dashboard asset."""

from importlib.resources import files

HTML = files("zittomind").joinpath("api/dashboard.html").read_text(encoding="utf-8")
