from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer
from typing import List
import sys

class Runner(App):

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, tests_dir: str="end-to-end-tests") -> None:
        self.tests_dir = tests_dir
        super().__init__()

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        tests = self.find_tests()
        self.table.add_columns("Test","Result")
        self.table.add_rows(tests)
        self.set_timer(2,self.change_one_test)

    def find_tests(self) -> List[str]:
        print("TODO find tests")
        return [
            ["foo test 1","Pending"],
            ["bar 2 test","OK"],
        ]

    def change_one_test(self) -> None:
        print("x")
        self.table.data[0][1] = "OK"
        self.table.refresh_cell(0,1)
        self.table._clear_caches()


if __name__ == "__main__":
    argc = len(sys.argv)
    tests_dir = None
    if argc == 2:
        tests_dir = sys.argv[1]
    elif argc > 2:
        print("Usage: python runner.py [TESTS_DIR]")
        sys.exit(2)

    app = Runner(tests_dir)
    app.run()
