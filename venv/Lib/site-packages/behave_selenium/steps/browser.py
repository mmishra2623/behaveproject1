from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from time import sleep
import contextlib
import io
import os
import queue
import threading
import warnings

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

IOHandler = namedtuple('IOHandler', ['thread', 'queue'])

HERE = os.path.dirname(__file__)

with open(os.path.join(HERE, "client.js"), "r") as client:
    JS_CLIENT = client.read()


class Browser:
    def __init__(self, command_executor='http://127.0.0.1:4444/wd/hub',
                 desired_capabilities=None):
        self.command_executor = command_executor
        if desired_capabilities is None:
            desired_capabilities = dict()
        self.desired_capabilities = desired_capabilities
        self.io = dict()
        self._driver = None
        self.driver_lock = threading.Lock()
        self.running = False
        self.wait_time = 0.1
        self.init_timeout = 3

    @contextlib.contextmanager
    def driver(self):
        with self.driver_lock:
            yield self._driver

    def pool_script(self, script, io_name):
        last_result = None
        while self.running:
            with self.driver() as driver:
                try:
                    result = driver.execute_script(script)
                except WebDriverException as exc:
                    warnings.warn("WebDriver exception received %s" % exc,
                                  RuntimeWarning)
                else:
                    if result != last_result and result is not None:
                        self.io[io_name].queue.put(result)
                        last_result = result
                    else:
                        last_result = None

            if last_result is None:
                # Sleep with the driver released to allow other threads
                # to acquire the lock.
                sleep(self.wait_time)

    def register_console_io(self):
        pool_script = """return window.__behave_selenium["log"].shift();"""

        io_handler = IOHandler(
            threading.Thread(
                target=self.pool_script,
                kwargs={
                    "script": pool_script,
                    "io_name": "console"}),
            queue.Queue())

        io_handler.thread.start()
        self.io["console"] = io_handler

    def register_DOM_io(self):
        io_handler = IOHandler(
            threading.Thread(
                target=self.pool_script,
                kwargs={
                    "script": "return window.__behave_selenium['_fn_getDOM']();",
                    "io_name": "dom"}),
                queue.Queue())
        io_handler.thread.start()
        self.io["dom"] = io_handler

    def initialize(self):
        self.running = True
        with self.driver() as driver:
            timeout = datetime.today() + timedelta(seconds=self.init_timeout)
            client_found = False
            while datetime.today() < timeout:
                try:
                    driver.execute_script("return window.__behave_selenium;")
                except WebDriverException as exc:
                    sleep(self.wait_time)
                else:
                    client_found = True
                    break

            if not client_found:
                # Install client from Selenium
                driver.execute_script(JS_CLIENT)

        self.register_console_io()
        self.register_DOM_io()

    def finalize(self):
        self.running = False

        for io in self.io.values():
            io.thread.join()

    def __enter__(self):
        self._driver = webdriver.Remote(
            command_executor=self.command_executor,
            desired_capabilities=self.desired_capabilities)
        self.start_time = datetime.today()

    def __exit__(self, *_):
        self.finalize()
        self._driver.quit()

    def check_stream(self, stream, *checks, timeout=None, encoding='utf-8'):
        checks = list(checks)

        # Initialize generators
        for check in checks:
            check.send(None)

        input_stream = self.io[stream].queue

        if timeout is None:
            def timedout():
                return False
        else:
            exceeded = self.start_time + timedelta(seconds=timeout)
            def timedout():
                return datetime.today() > exceeded

        while checks and not timedout():
            try:
                line = input_stream.get(block=True, timeout=0.1)
            except queue.Empty:
                if not self.running:
                    # The process exited
                    if any(io.thread.is_alive() for io in self.io.values()):
                        # Some reader is still running, we wait
                        continue
                    else:
                        # All readers finished, we exit
                        break
            else:
                for check in checks.copy():
                    try:
                        check.send(line)
                    except StopIteration as exc:
                        # Check success
                        checks.remove(check)

        for check in checks:
            check.close()

    def get(self, url):
        self.finalize()
        with self.driver() as driver:
            # This will wait for page to load
            result = driver.get(url)
        self.initialize()
        return result

    def execute_script(self, script):
        with self.driver() as driver:
            return driver.execute_script(script)
