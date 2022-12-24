# e2e-test-runner

<a href="https://raw.githubusercontent.com/cara-lang/e2e-test-runner/main/assets/screenshot.png"><img alt="Screenshot" src="https://github.com/cara-lang/e2e-test-runner/raw/main/assets/screenshot.png" width="400" /></a>

A runner for Cara E2E tests (see the [`end-to-end-tests`](https://github.com/cara-lang/compiler/tree/main/end-to-end-tests) directory in the [`cara-lang/compiler`](https://github.com/cara-lang/compiler) repo).

The expected structure of these tests is:
```
- tests_root
  - first_test
    - main.cara
    - stdout.txt
  - second_test
    - main.cara
    - stderr.txt
```
etc.

* If `stdout.txt` is present, it is required for the actual stdout to match it.
* If it's missing, no stdout is allowed.

* If `stderr.txt` is present, it is required for the actual stderr to match it.
* If it's missing, no stderr is allowed.
