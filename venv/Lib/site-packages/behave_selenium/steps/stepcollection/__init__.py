from argparse import Namespace
import contextlib
import imp
import inspect
import re
import sys
import types

from behave.parser import Parser
from behave.step_registry import StepRegistry
from behave.step_registry import names as step_names


class SubContext(Namespace):
    @contextlib.contextmanager
    def user_mode(self):
        """To keep Match.run happy."""
        yield


class SubSteps:
    def __init__(self, language=None, variant=None):
        self.parser = Parser(language=language, variant=variant)
        self.registry = StepRegistry()

        # Create decorators for the local registry
        for step_type in step_names.split():
            setattr(self, step_type, self.registry.make_decorator(step_type))

    @staticmethod
    def run_match(match, context):
        args = []
        kwargs = {}
        for arg in match.arguments:
            if arg.name is not None:
                kwargs[arg.name] = arg.value
            else:
                args.append(arg.value)

        return match.func(context, *args, **kwargs)

    def run(self, text, context):
        """
        Parse the given text and yield step functions.

        """
        steps = self.parser.parse_steps(text)
        for step in steps:
            match = self.registry.find_match(step)
            if match is None:
                raise ValueError("substep not found '%s'" % step)
            else:
                subcontext = SubContext(
                    table=step.table,
                    text=step.text,
                    step_context=context)
                yield self.run_match(match, context)


def define_steps(package_regex, step_module, translations, substeps=False):
    class BehaveStepCollectionLoader:
        def __init__(self, language, translation):
            self.language = language
            self.translation = translation

        def load_module(self, fullname):
            try:
                return sys.modules[fullname]
            except KeyError:
                pass

            module = imp.new_module(fullname)
            module.__file__ = step_module.__file__
            module.__doc__ = step_module.__doc__
            module.__path__ = []
            module.__loader__ = self
            module.LANG = self.language

            if substeps:
                module.substeps = SubSteps(language=self.language)
                step_decorator = module.substeps.step
            else:
                from behave import step as step_decorator


            members = inspect.getmembers(step_module, inspect.isfunction)
            for name, value in members:
                if name.startswith('_'):  # Private function
                    continue

                # Copy the function adding custom globals
                new_globals = value.__globals__.copy()
                new_globals['__language__'] = self.language

                function_copy = types.FunctionType(
                    value.__code__,
                    new_globals,
                    value.__name__,
                    value.__defaults__,
                    value.__closure__)

                for text in reversed(self.translation[name]):
                    value = step_decorator(text)(function_copy)

                setattr(module, name, value)

            sys.modules.setdefault(fullname, module)
            return module


    class BehaveStepCollectionFinder:
        module_pattern = re.compile(package_regex)

        def find_module(self, fullname, path=None):
            match = self.module_pattern.match(fullname) 
            if match:
                request_lang = match.group("lang")
                try:
                    translation = translations[request_lang]
                except KeyError:
                    return None
                else:
                    return BehaveStepCollectionLoader(request_lang,
                                                      translation)
            else:
                return None

    # Append the step finder to sys.meta_path
    sys.meta_path.append(BehaveStepCollectionFinder())
