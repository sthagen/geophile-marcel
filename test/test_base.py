import contextlib
import io
import os
import pathlib
import sys

import dill.source

import marcel.exception
import marcel.main
import marcel.util


class Test:

    start_dir = os.getcwd()

    def __init__(self, config_file='./.marcel.py'):
        self.main = None
        self.failures = 0
        self.reset_environment(config_file)

    def reset_environment(self, config_file='./.marcel.py'):
        sys.argv = [None, config_file]
        self.main = marcel.main.Main(same_process=True)
        os.system('sudo touch /tmp/farcel.log')
        os.system('sudo rm /tmp/farcel.log')
        os.chdir(Test.start_dir)

    def new_file(self, filename):
        path = pathlib.Path(filename)
        if path.exists():
            path.unlink()
        path.open()

    def check_ok(self, command, expected, actual):
        expected = self.remove_empty_line_at_end(expected.split('\n'))
        actual = self.remove_empty_line_at_end(actual.split('\n'))
        ok = True
        n = len(expected)
        if len(actual) == n:
            i = 0
            while ok and i < n:
                e = expected[i]
                a = actual[i]
                e_error = e.startswith('Error(') and e.endswith(')')
                a_error = a.startswith('Error(') and a.endswith(')')
                if e_error and a_error:
                    # Check that e message is a substring of a message
                    e_message = e[6:-1]
                    a_message = a[6:-1]
                    ok = e_message in a_message
                elif e_error or a_error:
                    ok = False
                else:
                    ok = a == e
                i += 1
        else:
            ok = False
        if not ok:
            print(f'{self.description(command)} failed:', file=sys.__stdout__)
            print(f'    expected:\n<<<{expected}>>>', file=sys.__stdout__)
            print(f'    actual:\n<<<{actual}>>>', file=sys.__stdout__)
            self.failures += 1

    def check_substring(self, command, expected, actual):
        if expected not in actual:
            print(f'{self.description(command)} failed. Expected substring not found in actual:', file=sys.__stdout__)
            print(f'    expected:\n<<<{expected}>>>', file=sys.__stdout__)
            print(f'    actual:\n<<<{actual}>>>', file=sys.__stdout__)
            self.failures += 1

    def fail(self, command, message):
        print(f'{self.description(command)} failed: {message}', file=sys.__stdout__)
        self.failures += 1

    def run_and_capture_output(self, command):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if type(command) is str:
                self.main.run_command(command)
            else:
                command()
        return out.getvalue(), err.getvalue()

    def run(self,
            test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        # test is the thing being tested. Usually it will produce output that can be used for verification.
        # For operations with side effects (e.g. rm), a separate verification command is needed.
        if verification is None and expected_out is None and expected_err is None and file is None:
            if type(test) is str:
                self.main.run_command(test)
            else:
                test()
        else:
            print(f'TESTING: {self.description(test)}')
            try:
                if verification is None:
                    actual_out, actual_err = self.run_and_capture_output(test)
                else:
                    self.run_and_capture_output(test)
                    actual_out, actual_err = self.run_and_capture_output(verification)
                if file:
                    actual_out = self.file_contents(file)
                if actual_err is not None and len(actual_err) > 0 and expected_err is None:
                    self.fail(test, f'Unexpected error: {actual_err}')
                if expected_out:
                    self.check_ok(test, self.to_string(expected_out), actual_out)
                if expected_err:
                    self.check_substring(test, expected_err, actual_err)
            except Exception as e:
                print(f'{self.description(test)}: Terminated by uncaught exception: {e}', file=sys.__stdout__)
                marcel.util.print_stack()
                self.failures += 1
            except marcel.exception.KillCommandException as e:
                print(f'{self.description(test)}: Terminated by KillCommandException: {e}', file=sys.__stderr__)

    def file_contents(self, filename):
        file = open(filename, 'r')
        contents = ''.join(file.readlines())
        file.close()
        return contents

    def to_string(self, x):
        if isinstance(x, str):
            return x
        elif isinstance(x, tuple) or isinstance(x, list):
            return '\n'.join([str(o) for o in x]) + '\n'
        else:
            return str(x)

    def delete_file(self, filename):
        os.remove(filename)

    def remove_empty_line_at_end(self, lines):
        if len(lines[-1]) == 0:
            del lines[-1]
        return lines

    def cd(self, path):
        self.main.run_command(f'cd {path}')

    def description(self, x):
        return x if type(x) is str else dill.source.getsource(x).split('\n')[0]
