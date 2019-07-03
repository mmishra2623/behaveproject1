from . import _steps
from ..stepcollection import define_steps
from .i18n import languages

define_steps(r"^behave_selenium\.steps\.naturalsearch\.(?P<lang>[^\.]+)$",
             _steps,
             languages,
             substeps=True)
