from rich.text import Text
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Static
from typing import List, Dict
import asyncio
import os
import subprocess
import sys

NOT_STARTED = "Not started"
PASSED = "Passed"
FAILED = "Failed"

STATUS = "Status"

TESTS_DIR = "end-to-end-tests"
#INTERPRETER = "_build/default/src/compiler.exe"
INTERPRETER = "./compiler_standin.sh"

class Summary(Static):
    def set_progress(self, done: int, total: int, passed: int) -> None:
        self.update(self.format(done, total, passed))
        if done == total:
            if passed == total:
                self.set_class(True,  "passed")
                self.set_class(False, "failed")
            else:
                self.set_class(False,  "passed")
                self.set_class(True, "failed")
                
    def format(self, done: int, total: int, passed: int) -> str:
        done_pct   = 0 if total == 0 else done*100.0/total
        passed_pct = 0 if total == 0 else passed*100.0/total
        return f"{done}/{total} tests done ({done_pct:.2f}%), {passed} passed ({passed_pct:.2f}%)"

class Runner(App):

    BINDINGS = [
        ("q",     "quit",          "Quit"),
        ("r",     "rerun",         "Rerun"),
        ("space", "filter_passed", "Show/hide passed tests"),
    ]

    CSS_PATH = "app.css"

    #####################################################
    # Custom state

    tests = reactive({})
    hide_passed = reactive(False)
    done   = reactive(0)
    total  = reactive(0)
    passed = reactive(0)

    def get_key_display(self, key: str) -> str:
        if key == "space": return "Space"
        return super().get_key_display(key)

    def compose(self) -> ComposeResult:
        self.summary = Summary()
        yield self.summary

        self.table = DataTable()
        yield self.table

        yield Footer()

    #####################################################
    # Lifecycle

    async def on_mount(self) -> None:
        self.summary.set_progress(0,0,0)

        self.tests = self.find_tests()

        self.table.add_columns("Test",STATUS)
        self.total = len(self.tests)

        await self.run_tests()

    #####################################################
    # Actions

    def action_filter_passed(self) -> None:
        self.hide_passed = not self.hide_passed
        if self.hide_passed:
            self.table.columns[1].label = f"{STATUS} -P"
        else:
            self.table.columns[1].label = STATUS

    def action_rerun(self) -> None:
        assert False, "TODO implement action_rerun"

    #####################################################
    # Watches

    def watch_hide_passed(self, old: bool, new: bool) -> None:
        self.redraw_table()

    def watch_tests(self, old, new) -> None:
        self.redraw_table()

    def watch_total(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed)

    def watch_done(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed)

    def watch_passed(self, old: int, new: int) -> None:
        self.summary.set_progress(self.done, self.total, self.passed)

    #####################################################
    # Custom


    def status_text(self, status: str):
        style = None
        if status == PASSED:
            style = "green"
        elif status == FAILED:
            style = "red"
        return Text(status, style=style)

    def redraw_table(self) -> None:
        self.table.clear()
        if self.hide_passed:
            items = [[k,self.status_text(v)] for k,v in self.tests.items() if v != PASSED]
        else:
            items = [[k,self.status_text(v)] for k,v in self.tests.items()]
        self.table.add_rows(sorted(items))
        self.table._clear_caches()

    def set_test_status(self, test_name: str, new_status: str) -> None:
        if new_status != NOT_STARTED and self.tests[test_name] == NOT_STARTED:
            self.done += 1
            if new_status == PASSED:
                self.passed += 1
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

        wanted_stdout_path = f"{TESTS_DIR}/{test_name}/stdout.txt"
        wanted_stderr_path = f"{TESTS_DIR}/{test_name}/stderr.txt"

        if os.path.exists(wanted_stdout_path):
            with open(wanted_stdout_path, 'r') as f:
                wanted_stdout = f.read()
                if wanted_stdout != stdout:
                    self.set_test_status(test_name, FAILED)
                    return

        if os.path.exists(wanted_stderr_path):
            with open(wanted_stderr_path, 'r') as f:
                wanted_stderr = f.read()
                if wanted_stderr != stderr:
                    self.set_test_status(test_name, FAILED)
                    return

        self.set_test_status(test_name, PASSED)

if __name__ == "__main__":
    app = Runner()
    asyncio.run(app.run_async())
