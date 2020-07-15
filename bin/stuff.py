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


class App:
    """Helper class for working with envs, args, streams, and exit codes."""

    # Set class attributes to enable dependency injection for instances.
    from os import environ
    from sys import argv
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    stderr = sys.stderr.buffer
    exit = SystemExit

    def error(self, *messages):
        message = '\n\n'.join(map(str, messages))
        return self.exit(message)

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


class CLI(App):
    """Command line interface helper class."""

    commands = {}

    def __init_subclass__(cls):
        """Make sure subclasses define a help message."""
        assert cls.__doc__ is not None, cls

    @register(commands)
    def help(self, *args):
        """Output detailed help for the program or a command."""
        if not args:
            message = f"{self.__doc__}\n\n{self.usage()}"
        else:
            name = args[0]  # Ignore subsequent args.
            message = self.info(name)
        self.emit_text(message)

    def info(self, name):
        """Return usage info for the given command."""
        try:
            command = self.commands[name]
        except KeyError:
            raise self.error(self.usage(), f"Error: no command named {name!r}")
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
        return '\n'.join(self._usage())

    def _usage(self, *, indent='    '):
        prefix = f"{indent}{__file__} "
        summaries = {name: self.summary(name) for name in self.commands}
        width = max(len(x) for x in summaries) + len(indent)
        yield "Usage:"
        for usage, summary in summaries.items():
            if summary:
                yield f"{prefix}{usage:{width}}{summary}"
            else:
                yield f"{prefix}{usage}"

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
            raise self.error(self.usage(), f"Error: no command named {name!r}")

        try:
            return command(self, *args)
        except TypeError as exc:
            raise self.error(self.info(name), f"Error: {exc}")

    @classmethod
    def run(cls):
        cls()()


class AutoCommandCLI(CLI):
    """Auto-register commands from public methods."""

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.commands = cls.commands.copy()  # Copy value from parent class.
        for name, value in vars(cls).items():
            if not name.startswith('_') and callable(value):
                register(cls.commands)(value)


class Stuff:

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.buffer = bytearray(2048)

    def key(self, stream):
        """Read the data stream and return the key."""
        hasher = sha256()
        for chunk in chunks(stream.readinto1, self.buffer):
            hasher.update(chunk)
        return hasher.hexdigest()

    def transfer(self, instream, outstream):
        """Transfer data between streams and return the key."""
        hasher = sha256()
        for chunk in chunks(instream.readinto1, self.buffer):
            hasher.update(chunk)
            outstream.write(chunk)
        return hasher.hexdigest()

    def path(self, key):
        """Return the path to the cache file for the key."""
        return join(self.data_dir, key)

    def store(self, stream):
        """Write the data from the stream to cache and return its key."""
        with NamedTemporaryFile(delete=False) as file:
            temp_path = file.name
            key = self.transfer(stream, file)
        move(temp_path, self.path(key))
        return key

    def list(self):
        """Return all stored keys."""
        return listdir(self.data_dir)

    def get(self, key, stream):
        """Write the data for the key from cache to the stream."""
        path = self.path(key)
        with open(path, 'rb') as file:
            computed_key = self.transfer(file, stream)
        stream.flush()
        if computed_key != key:
            raise Exception(f"detected data corruption in {path}")


class StuffCLI(AutoCommandCLI):
    """stuff: a minimal content addressable storage utility"""

    def __init__(self):
        root_dir = self.environ.get('STUFF', dirname(dirname(__file__)))
        data_dir = join(root_dir, 'data')
        makedirs(data_dir, exist_ok=True)
        self.stuff = Stuff(data_dir)

    def key(self):
        """Output the key for the data from stdin."""
        self.emit_text(self.stuff.key(self.stdin))

    def get(self, key):
        """Output the data for the given key.

        Usage: `stuff get <key>`

        Example (bash):

            $ stuff get e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

        """  # noqa
        try:
            self.stuff.get(key, self.stdout)
        except FileNotFoundError:
            raise self.error(f"Error: could not retrieve data for {key}")

    def path(self, key):
        """Output the path to the cache file for the given key."""
        self.emit_text(self.stuff.path(key))

    def store(self):
        """Store the data from stdin and output its key.

        Example (bash):

            $ printf "ayy lmao" > file.txt
            $ key=$(stuff store < file.txt)
            $ echo "$key"
            363bd719f9697e46e6514bf1f0efce0e5ace75683697fb820065a05c8fb3135e
            $ stuff get "$key"
            ayy lmao

        """
        key = self.stuff.store(self.stdin)
        self.emit_text(key)

    def list(self):
        """Output all stored keys."""
        for path in self.stuff.list():
            self.emit_text(path)

    def download(self, url):
        """Download and store data from the given URL."""
        raise NotImplementedError


if __name__ == '__main__':
    StuffCLI.run()
