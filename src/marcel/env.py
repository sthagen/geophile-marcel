import getpass
import os
import pathlib
import socket

import marcel.exception
import marcel.object.cluster
import marcel.object.colorscheme
import marcel.object.colorscheme
from marcel.util import *


marker = 0

class EnvVar(str):

    def __init__(self, value):
        super().__init__()
        self.value = value
        global marker
        self.marker = marker
        marker += 1

    def __str__(self):
        return f'{self.value}({self.marker})'

    def set(self, value):
        self.value = value
        global marker
        self.marker = marker
        marker += 1


class Environment:

    def __init__(self, config_file):
        self._user = getpass.getuser()
        self._homedir = pathlib.Path.home().resolve()
        self._current_dir = pathlib.Path.cwd().resolve()
        self._host = socket.gethostname()
        self._vars = {  # Environment variables
            'USER': EnvVar(self._user),
            'HOME': EnvVar(self._homedir.as_posix()),
            'HOST': EnvVar(self._host),
            'PWD': EnvVar(self._current_dir.as_posix())
        }
        self._config = marcel.config.Configuration(self._vars)
        self._config.read_config(config_file)
        self._colors = self._config.colors
        self._color_scheme = self._config.color_scheme

    def prompts(self):
        return (self._prompt_string(self._config.prompt),
                self._prompt_string(self._config.continuation_prompt))

    def pwd(self):
        return self._current_dir

    def cd(self, directory):
        assert isinstance(directory, pathlib.Path), directory
        new_dir = self._current_dir / directory
        try:
            self._current_dir = new_dir.resolve(strict=True)
            self._vars['PWD'].set(self._current_dir.as_posix())
            # So that executables have the same view of the current directory.
            os.chdir(self._current_dir)
        except FileNotFoundError:
            raise marcel.exception.KillCommandException(
                'Cannot cd into {} from {}. Directory does not exist.'.format(directory, self._current_dir))

    def globals(self):
        return self._vars

    def cluster(self, name):
        symbol = self._vars.get(name, None)
        return (symbol.value
                if symbol and isinstance(symbol.value, marcel.object.cluster.Cluster) else
                None)

    def config(self):
        return self._config

    def color_scheme(self):
        assert isinstance(self._color_scheme, marcel.object.colorscheme.ColorScheme), self._color_scheme
        return self._color_scheme

    def getenv(self, var):
        var = self._vars.get(var, None)
        return var.value if var else None

    def _prompt_string(self, prompt_pieces):
        buffer = []
        color = None
        for x in prompt_pieces:
            # In each iteration, we either have a color, or a prompt component. In the latter case,
            # append it to the buffer, colorizing if color is defined.
            if isinstance(x, marcel.object.colorscheme.Color):
                color = x
                x = None
            elif isinstance(x, str):
                if isinstance(x, EnvVar):
                    print(f'_prompt_string: {x}')
                c = self._colors.get(x, None)
                if c:
                    color = c
                    x = None
            elif callable(x):
                x.__globals__.update(self._config.globals_for_op_functions)
                x = x()
            else:
                raise marcel.exception.KillShellException(f'Invalid prompt component: {x}')
            if x:
                x = str(x)
                buffer.append(colorize(x, color) if color else x)
        return ''.join(buffer)
