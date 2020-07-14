#!/usr/bin/env python3
"""WIP Python implementation."""
import sys
from hashlib import sha256
from os import listdir, makedirs
from os.path import dirname, join
from shutil import move
from tempfile import NamedTemporaryFile


def chunks(readinto, buffer):
    """Read chunks of bytes into the provided buffer.

    Yields memoryview slices of the buffer to avoid unnecessary copies.

    >>> from io import BytesIO

    >>> input = BytesIO(b'ayy lmao')
    >>> buffer = bytearray(3)
    >>> for chunk in chunks(input.readinto, buffer):
    ...     print(buffer, chunk.tobytes())
    bytearray(b'ayy') b'ayy'
    bytearray(b' lm') b' lm'
    bytearray(b'aom') b'ao'

    """
    assert len(buffer) > 0
    view = memoryview(buffer)
    while True:
        bytes_read = readinto(buffer)
        if not bytes_read:
            break
        # Slice the memoryview to avoid copying data from the buffer.
        yield view[:bytes_read]


def relay(readinto, consume, *, buffer=None):
    """Relay chunks of bytes from a producer to a consumer.

    >>> from io import BytesIO

    >>> out = BytesIO()
    >>> relay(BytesIO(b'ayy lmao').readinto, out.write)
    >>> out.getvalue()
    b'ayy lmao'

    >>> relay(
    ...     readinto=BytesIO(b'ayy lmao').readinto,
    ...     consume=lambda x: print(x.tobytes()),
    ...     buffer=bytearray(2),
    ...  )
    b'ay'
    b'y '
    b'lm'
    b'ao'

    """
    if buffer is None:
        buffer = bytearray(2048)
    for chunk in chunks(readinto, buffer):
        consume(chunk)


def register(dct, names=()):
    """Add an object to a dict by its name."""
    def registerer(obj):
        for name in names or [obj.__name__.replace('_', '-')]:
            assert isinstance(name, str), name
            assert name not in dct, name
            dct[name] = obj
        return obj
    return registerer


def get_doc(obj, default=''):
    doc = obj.__doc__
    if doc is None:
        return default
    stripped = doc.strip()
    if not stripped:
        return default
    return stripped


class CLI:
    """Command line interface helper class."""

    # Set class attributes to enable dependency injection for instances.
    from os import environ
    from sys import argv
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    stderr = sys.stderr.buffer
    exit = SystemExit

    LINE_END = b'\n'

    def emit(self, chunk):
        """Write bytes to stdout."""
        self.stdout.write(chunk)
        self.stdout.flush()

    def emit_text(self, obj):
        """Write text to stdout."""
        self.stdout.write(str(obj).encode())
        self.stdout.write(self.LINE_END)
        self.stdout.flush()

    def log(self, obj):
        """Write text to stderr."""
        self.stderr.write(str(obj).encode())
        self.stderr.write(self.LINE_END)
        self.stderr.flush()

    def lines(self):
        """Yield lines from stdin until EOF, without trailing separators."""
        # TODO: Support alternate line delimiters / tokenization.
        for line in self.stdin:
            yield line.rstrip(self.LINE_END)

    def usage(self):
        """Return a usage message."""
        return self.__doc__

    def __init_subclass__(cls):
        """Make sure subclasses define a usage message."""
        assert cls.__doc__ is not None, cls

    def __call__(self):
        """Run the CLI."""
        raise NotImplementedError

    @classmethod
    def run(cls):
        cls()()


class CommandCLI(CLI):
    """Command line interface supporting multiple commands."""

    commands = {}

    @register(commands)
    def help(self, *args):
        """Output detailed help for the program or a command."""
        if not args:
            message = self.usage()
        else:
            name = args[0]  # Ignore subsequent args.
            message = self.info(name)
        self.emit_text(message)

    def error(self, message):
        """Log usage and exit."""
        self.log(self.usage())
        self.log(f"\nError: {message}")
        return self.exit(1)

    def info(self, name):
        """Return usage info for the given command."""
        try:
            command = self.commands[name]
        except KeyError:
            raise self.error(f"no command named {name!r}")
        doc = get_doc(command, "<no help available>")
        return f"{__file__} {name}: {doc}"

    def summary(self, name, default=''):
        """Return the first line of the command's usage info."""
        command = self.commands[name]
        doc = get_doc(command)
        if not doc:
            return default
        return doc.splitlines()[0]

    def usage(self):
        """Return a usage message."""
        return '\n'.join([super().usage(), '', "Usage:", *self._usages(), ''])

    def _usages(self, *, indent='    ', **kwargs):
        """Return usage help for each command."""
        prefix = f"{indent}{__file__} "
        summaries = {name: self.summary(name) for name in self.commands}
        width = max(len(x) for x in summaries) + len(indent)
        return [
            f"{prefix}{usage:{width}}{summary}"
            if summary else f"{prefix}{usage}"
            for usage, summary in summaries.items()
        ]

    def __call__(self):
        """Run the specified command."""
        try:
            _, name, *args = self.argv
        except ValueError:
            return self.help()

        if name in ['-h', '--help']:
            return self.help()

        try:
            command = self.commands[name]
        except KeyError:
            raise self.error(f"no command named {name!r}")

        try:
            return command(self, *args)
        except TypeError as exc:
            raise self.error(exc)


class AutoCommandCLI(CommandCLI):
    """Auto-register commands from public methods."""

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.commands = cls.commands.copy()  # Copy value from parent class.
        for name, value in vars(cls).items():
            if not name.startswith('_') and callable(value):
                register(cls.commands)(value)


class fanout(list):
    def __call__(self, *args, **kwargs):
        for func in self:
            func(*args, **kwargs)


class StuffCLI(AutoCommandCLI):
    """stuff: a minimal content addressable storage utility"""

    DATA_DIR = 'data'

    def __init__(self):
        try:
            self.root_dir = self.environ['STUFF']
        except KeyError:
            self.root_dir = dirname(dirname(__file__))
        self.data_dir = join(self.root_dir, self.DATA_DIR)
        makedirs(self.data_dir, exist_ok=True)

    def key(self):
        """Output the key for the data from stdin."""
        hasher = sha256()
        relay(self.stdin.readinto1, hasher.update)
        key = hasher.hexdigest()
        self.emit_text(key)

    def get(self, key):
        """Output the data for the given key."""
        raise NotImplementedError

    def _path(self, *components):
        return join(self.root_dir, *components)

    def _path_for(self, key):
        return join(self.data_dir, key)

    def path(self, key):
        """Output the filesystem path for the given key."""
        self.emit_text(self._path_for(key))

    def store(self):
        """Store the data from stdin and output its key."""
        hasher = sha256()
        with NamedTemporaryFile(delete=False) as f:
            name = f.name
            relay(self.stdin.readinto1, fanout([f.write, hasher.update]))
        key = hasher.hexdigest()
        path = self._path_for(key)
        move(name, path)
        self.emit_text(key)

    def list(self):
        """Output all stored keys."""
        for path in listdir(self.data_dir):
            self.emit_text(path)

    def download(self, url):
        """Download and store data from the given URL."""
        raise NotImplementedError


if __name__ == '__main__':
    StuffCLI.run()
