# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import os
import pathlib

from prompt_toolkit.completion import Completer, Completion

import marcel.core
import marcel.doc
import marcel.exception
import marcel.op
import marcel.parser
import marcel.util

DEBUG = True

SINGLE_QUOTE = "'"
DOUBLE_QUOTE = '"'
QUOTES = SINGLE_QUOTE + DOUBLE_QUOTE
NL = '\n'


def debug(message):
    if DEBUG:
        print(message, flush=True)


class TabCompleter(Completer):

    OPS = marcel.op.public
    HELP_TOPICS = list(marcel.doc.topics) + OPS

    def __init__(self, env):
        self.env = env
        self.parser = None

    def get_completions(self, document, complete_event):
        debug(f'get_completions: doc=<{document}> ------------------------------------------------------------')
        token = self.parse(document.text)
        last_token_context = self.parser.op_arg_context
        if last_token_context.is_op():
            completer = self.complete_op
        elif last_token_context.is_flag():
            completer = self.complete_flag
        elif last_token_context.is_arg():
            completer = self.complete_arg
        else:
            assert False, last_token_context
        for c in completer(token):
            yield c

    def parse(self, line):
        # Parse the text so far, to get information needed for tab completion. It is expected that
        # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
        # which can be ignored. The important point is that the parse will set Parser.op.
        self.parser = marcel.parser.Parser(line, self.env)
        try:
            self.parser.parse()
        except marcel.exception.MissingQuoteException as e:
            debug(f'Caught MissingQuoteException: <{e.quote}{e.unterminated_string}>')
        except marcel.exception.KillCommandException as e:
            # Parse may have failed because of an unrecognized op, for example. Normal continuation should
            # do the right thing.
            debug(f'Caught KillCommandException: {e}')
        except BaseException as e:
            debug(f'Something went wrong: {e}')
            marcel.util.print_stack_of_current_exception()
        else:
            debug('No exception during parse')
        token = self.parser.token.value()
        if (missing_quote := self.parser.token.missing_quote()) is not None:
            print(f'missing_quote: {missing_quote}, token: {token}')
            token = missing_quote + token
        return token

    def complete_op(self, token):
        debug(f'complete_op: token={token}')
        # Include marcel ops.
        # Include executables only if there are no qualifying ops.
        found_op = False
        for op in TabCompleter.OPS:
            if len(token) == 0 or op.startswith(token):
                yield TabCompleter.completion(token, op)
                found_op = True
        if not found_op:
            for exe in TabCompleter.executables():
                if exe.startswith(token):
                    yield TabCompleter.completion(token, exe)

    def complete_flag(self, token):
        debug(f'complete_flag: token={token}')
        for flag in self.parser.flags():
            if flag.startswith(token):
                yield TabCompleter.completion(token, flag)

    # Arg completion assumes we're looking for filenames. (bash does this too.)
    def complete_arg(self, token):
        debug(f'complete_arg: token={token}')
        current_dir = self.env.dir_state().current_dir()
        quote = None
        if token:
            # Separate quote and token if necessary
            if token[0] in QUOTES:
                quote = token[0]
                token = token[1:]
            if token.startswith('~/') and quote != DOUBLE_QUOTE:
                if token == '~/':
                    if quote != DOUBLE_QUOTE:
                        home = pathlib.Path(token).expanduser()
                        filenames = os.listdir(home.as_posix())
                elif token.startswith('~/'):
                    base = pathlib.Path('~/').expanduser()
                    base_length = len(base.as_posix())
                    pattern = token[2:] + '*'
                    filenames = ['~' + f[base_length:]
                                 for f in [p.as_posix() for p in base.glob(pattern)]]
            elif token.startswith('~') and quote is None:
                find_user = token[1:]
                filenames = []
                for username in TabCompleter.usernames():
                    if username.startswith(find_user):
                        filenames.append('~' + username)
            elif token.startswith('/'):
                base = '/'
                pattern_prefix = token[1:]
                filenames = [p.as_posix()
                             for p in pathlib.Path(base).glob(pattern_prefix + '*')]
            else:
                base = current_dir
                pattern_prefix = token
                filenames = [p.relative_to(base).as_posix()
                             for p in pathlib.Path(base).glob(pattern_prefix + '*')]
        else:
            # All filenames in current directory
            filenames = [p.relative_to(current_dir).as_posix() for p in current_dir.iterdir()]
        # Append / to dirs
        filenames = [f + '/' if pathlib.Path(f).expanduser().is_dir() else f for f in filenames]
        if len(filenames) == 1:
            if not filenames[0].endswith('/'):
                filenames = [filenames[0] + ' ']
        debug(f'complete_filename: candidates for {token}: {filenames}')
        return filenames

    @staticmethod
    def complete_help(text):
        debug(f'complete_help, text = <{text}>')
        candidates = []
        for topic in TabCompleter.HELP_TOPICS:
            if topic.startswith(text):
                candidates.append(topic)
        debug(f'complete_help candidates for <{text}>: {candidates}')
        return candidates


    @staticmethod
    def op_name(line):
        first = line.split()[0]
        return first if first in TabCompleter.OPS else None

    @staticmethod
    def executables():
        executables = []
        path = os.environ['PATH'].split(':')
        for p in path:
            for f in os.listdir(p):
                if marcel.util.is_executable(f) and f not in executables:
                    executables.append(f)
        return executables

    @staticmethod
    def usernames():
        usernames = []
        with open('/etc/passwd', 'r') as passwds:
            users = passwds.readlines()
        for line in users:
            fields = line.split(':')
            username = fields[0]
            usernames.append(username)
        return usernames

    @staticmethod
    def completion(token, completion):
        return Completion(text=f'{completion[len(token):]} ',
                          display=completion)
