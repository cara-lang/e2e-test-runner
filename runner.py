from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Static
from typing import List, Dict
import os
import sys

NOT_STARTED = "Not started"
PASSED = "Passed"
FAILED = "Failed"

STATUS = "Status"

class Summary(Static):
    def set_progress(self, done: int, total: int, passed: int) -> None:
        self.update(self.format(done, total, passed))
        if done == total:
            if passed == total:
                self.set_class("passed")
            else:
                self.set_class("failed")
                
    def format(self, done: int, total: int, passed: int) -> str:
        done_pct   = 0 if total == 0 else done*1.0/total
        passed_pct = 0 if total == 0 else passed*1.0/total
        return f"{done}/{total} tests done ({done_pct:.2f}%), {passed} passed ({passed_pct:.2f}%)"

class Runner(App):

    BINDINGS = [
        ("q",     "quit",          "Quit"),
        ("space", "filter_passed", "Show/hide passed tests"),
    ]

    CSS_PATH = "app.css"

    #####################################################
    # Custom state

    tests_dir = "end-to-end-tests"
    tests     = reactive({})
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

    def on_mount(self) -> None:
        self.summary.set_progress(0,0,0)

        self.tests = self.find_tests()
        self.run_tests()

        self.table.add_columns("Test",STATUS)
        self.table.add_rows(sorted([[k,v] for k,v in self.tests.items()]))

    #####################################################
    # Actions

    def action_filter_passed(self) -> None:
        self.hide_passed = not self.hide_passed
        if self.hide_passed:
            self.table.columns[1].label = f"{STATUS} -P"
        else:
            self.table.columns[1].label = STATUS

    #####################################################
    # Watches

    def watch_hide_passed(self, old: bool, new: bool) -> None:
        self.table.clear()
        if new:
            self.table.add_rows(sorted([[k,v] for k,v in self.tests.items()
                                        if v != PASSED]))
        else:
            self.table.add_rows(sorted([[k,v] for k,v in self.tests.items()]))

    #####################################################
    # Custom

    def set_test_status(self, test_name: str, new_status: str) -> None:
        self.tests[test_name] = new_status

        (idx,_) = next(filter(lambda i,row: row[0] == test_name, enumerate(self.table.data)))
        self.table.data[idx][1] = new_status
        self.table.refresh_cell(idx,1)

        # TODO: Expensive. Shouldn't be needed but currently is,
        # at least as of textual 0.8.0
        self.table._clear_caches()

    def find_tests(self) -> Dict[str, str]:
        return {os.path.basename(d[0]):NOT_STARTED for d in os.walk(self.tests_dir)}

    def run_tests(self) -> None:
        # TODO
        pass


if __name__ == "__main__":
    app = Runner()
    app.run()
