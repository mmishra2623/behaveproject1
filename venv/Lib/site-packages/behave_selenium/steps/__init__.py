from . import _steps
from . import browser
from .i18n import languages
from .stepcollection import define_steps

define_steps(r"^behave_selenium\.steps\.(?P<lang>[^\.]+)$",
             _steps,
             languages)
