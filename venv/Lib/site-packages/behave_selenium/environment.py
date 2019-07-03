from contextlib import ExitStack


def before_scenario(context, scenario):
    context.selenium_browsers = dict()
    context.selenium_exitstack = ExitStack().__enter__()


def after_scenario(context, scenario):
    context.selenium_exitstack.close()
