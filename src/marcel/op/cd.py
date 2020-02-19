"""C{cd DIRECTORY}

Change the current directory to the given directory.

TODO: no args -> home directory
TODO: .. and .
"""

import pathlib


def cd():
    return Cd()


class CdArgParser(marcel.osh.core.OshArgParser):

    def __init__(self):
        super().__init__('cd')
        self.add_argument('directory',
                          nargs='?',
                          default='0')


class Cd(marcel.osh.core.Op):

    argparser = CdArgParser()

    def __init__(self):
        super().__init__()
        self.directory = None

    def __repr__(self):
        return 'cd(directory=%s)' % self.directory

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        self.directory = pathlib.Path(self.directory)

    def receive(self, x):
        assert x is None, x
        marcel.osh.env.ENV.cd(self.directory)

    # Op

    def arg_parser(self):
        return Cd.argparser