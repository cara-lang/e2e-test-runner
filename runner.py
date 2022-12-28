from rich.text import Text
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Static
from textual.containers import Horizontal, Vertical
from typing import List, Dict
import asyncio
import os
import subprocess
import sys

NOT_STARTED = "Not started"
PASSED = "Passed"
FAILED = "Failed"
DIFF_ERR = "Different error"

STATUS = "Status"

TESTS_DIR = "end-to-end-tests"
INTERPRETER = "_build/default/src/compiler.exe"

class Summary(Static):
    def set_progress(self, done: int, total: int, passed: int, diff_err: int) -> None:
        self.update(self.format(done, total, passed, diff_err))
        if done == total:
            if passed == total:
                self.set_class(True,  "passed")
                self.set_class(False, "failed")
            else:
                self.set_class(False, "passed")
                self.set_class(True,  "failed")
                
    def format(self, done: int, total: int, passed: int, diff_err: int) -> str:
        return f"{done}/{total} tests done, {passed} passed, {diff_err} differ in error"

class Table(DataTable):
    def watch_cursor_cell(self, old, new):
        for watcher in self.cursor_cell_watchers:
            watcher(old,new)
        return super().watch_cursor_cell(old,new)

class Runner(App):

    BINDINGS = [
        ("q",     "quit",          "Quit"),
        ("r",     "rerun",         "Rerun"),
        ("space", "filter_passed", "Show/hide passed tests"),
    ]

    CSS_PATH = "app.css"

    #####################################################
    # Custom state

    tests        = reactive({})
    tests_stdout_actual   = reactive({})
    tests_stdout_expected = reactive({})
    tests_stderr_actual   = reactive({})
    tests_stderr_expected = reactive({})
    hide_passed = reactive(False)
    done     = reactive(0)
    total    = reactive(0)
    passed   = reactive(0)
    diff_err = reactive(0)

    def get_key_display(self, key: str) -> str:
        if key == "space": return "Space"
        return super().get_key_display(key)

    def compose(self) -> ComposeResult:
        self.summary = Summary()
        yield self.summary

        self.table = Table()
        self.table.cursor_cell_watchers = [self.watch_table_cursor_cell]
        yield self.table

        self.diff = Vertical(
                Static("Click on a test to see its output", classes="diff-test-name"),
                Horizontal(
                    Vertical(
                        Static("stdout", classes="diff-column-title"),
                        Vertical(
                            Static("Actual:",   classes="diff-column-section"),
                            Static("", classes="diff-content"),
                            Static("Expected:", classes="diff-column-section"),
                            Static("", classes="diff-content"),
                            classes="diff-column-output",
                            ),
                        classes="diff-column",
                        ),
                    Vertical(
                        Static("stderr", classes="diff-column-title"),
                        Vertical(
                            Static("Actual:",   classes="diff-column-section"),
                            Static("", classes="diff-content"),
                            Static("Expected:", classes="diff-column-section"),
                            Static("", classes="diff-content"),
                            classes="diff-column-output",
                            ),
                        classes="diff-column",
                        ),
                    classes="diff-columns",
                    ),
                classes="diff"
                )
        yield self.diff

        yield Footer()

    #####################################################
    # Lifecycle

    async def on_mount(self) -> None:
        self.summary.set_progress(0,0,0,0)
        self.tests = self.find_tests()
        self.table.add_columns("Test",STATUS)
        await self.run_tests()

    #####################################################
    # Actions

    def action_filter_passed(self) -> None:
        self.hide_passed = not self.hide_passed
        if self.hide_passed:
            self.table.columns[1].label = f"{STATUS} -P"
        else:
            self.table.columns[1].label = STATUS

    async def action_rerun(self) -> None:
        self.tests_stdout_actual   = {}
        self.tests_stdout_expected = {}
        self.tests_stderr_actual   = {}
        self.tests_stderr_expected = {}

        self.done = 0
        self.passed = 0
        self.diff_err = 0
        self.total = 0

        self.tests = self.find_tests()

        await self.run_tests()
        self.redraw_table()

    #####################################################
    # Watches

    def watch_hide_passed(self, old: bool, new: bool) -> None:
        self.redraw_table()

    def watch_tests(self, old, new) -> None:
        self.total = len(self.tests)
        self.redraw_table()

    def watch_table_cursor_cell(self, old, new) -> None:
        test_name = self.table.data[new.row][0]

        # TODO is there a way to do this with IDs? Maybe create our own class with reactives...
        diff_test_name = self.diff.children[0]
        diff_stdout_actual   = self.diff.children[1].children[0].children[1].children[1]
        diff_stdout_expected = self.diff.children[1].children[0].children[1].children[3]
        diff_stderr_actual   = self.diff.children[1].children[1].children[1].children[1]
        diff_stderr_expected = self.diff.children[1].children[1].children[1].children[3]

        diff_test_name.update(test_name)
        diff_stdout_actual.update(  self.tests_stdout_actual.get(  test_name, ""))
        diff_stdout_expected.update(self.tests_stdout_expected.get(test_name, ""))
        diff_stderr_actual.update(  self.tests_stderr_actual.get(  test_name, ""))
        diff_stderr_expected.update(self.tests_stderr_expected.get(test_name, ""))

    def watch_total(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed, self.diff_err)

    def watch_done(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed, self.diff_err)

    def watch_passed(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed, self.diff_err)

    def watch_diff_err(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed, self.diff_err)

    #####################################################
    # Custom


    def status_text(self, status: str):
        style = None
        if status == PASSED:
            style = "green reverse"
        elif status == DIFF_ERR:
            style = "yellow reverse"
        elif status == FAILED:
            style = "red"
        return Text(status, style=style)

    def redraw_table(self) -> None:
        self.table.clear()
        if self.hide_passed:
            items = [[k,self.status_text(v)] for k,v in self.tests.items() if v != PASSED and v != DIFF_ERR]
        else:
            items = [[k,self.status_text(v)] for k,v in self.tests.items()]
        self.table.add_rows(sorted(items))
        self.table._clear_caches()

    def set_test_status(self, test_name: str, new_status: str) -> None:
        if new_status != NOT_STARTED and self.tests[test_name] == NOT_STARTED:
            self.done += 1
            if new_status == PASSED:
                self.passed += 1
            elif new_status == DIFF_ERR:
                self.diff_err += 1
        self.tests[test_name] = new_status
        self.redraw_table()

    def find_tests(self) -> Dict[str, str]:
        return {os.path.basename(d[0]):NOT_STARTED 
                for d in os.walk(TESTS_DIR) 
                if d[0] != TESTS_DIR
                }

    async def run_tests(self):
        coroutines = [self.run_test(test_name)
                      for test_name,status in self.tests.items()
                      if status == NOT_STARTED]
        return asyncio.gather(*coroutines)

    async def run_test(self, test_name: str):
        process = await asyncio.create_subprocess_exec(
                INTERPRETER,
                f"{TESTS_DIR}/{test_name}/main.cara",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                )
        stdout,stderr = await process.communicate()
        stdout = stdout.decode("utf-8")
        stderr = stderr.decode("utf-8")

        wanted_stdout_path = f"{TESTS_DIR}/{test_name}/stdout.txt"
        wanted_stderr_path = f"{TESTS_DIR}/{test_name}/stderr.txt"

        self.tests_stdout_actual[test_name] = stdout
        self.tests_stderr_actual[test_name] = stderr

        if os.path.exists(wanted_stdout_path):
            with open(wanted_stdout_path, 'r') as f:
                wanted_stdout = f.read()
                self.tests_stdout_expected[test_name] = wanted_stdout
                if wanted_stdout != stdout:
                    self.set_test_status(test_name, FAILED)
        else:
            if stdout != "":
                self.set_test_status(test_name, FAILED)

        if os.path.exists(wanted_stderr_path):
            with open(wanted_stderr_path, 'r') as f:
                wanted_stderr = f.read()
                self.tests_stderr_expected[test_name] = wanted_stderr
                if wanted_stderr != stderr:
                    self.set_test_status(test_name, DIFF_ERR)
        else:
            if stderr != "":
                self.set_test_status(test_name, FAILED)

        if self.tests[test_name] == NOT_STARTED: # if not failed
            self.set_test_status(test_name, PASSED)

if __name__ == "__main__":
    app = Runner()
    asyncio.run(app.run_async())

