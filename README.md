# stuff

Rudimentary content-addressable storage: a key-value store whose keys
are derived from the values.

Arbitrary data may be stored in the `data` directory, in a file whose
name is the SHA-256 hash of its contents. (Note that the file named
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` is
empty: its name is the SHA-256 hash of the empty string.)

When attempting to retrieve data, if it is not stored in the local
repository, the data may still be retrieved if a procedure for
retrieving or deriving it is known.

A common type of procedure is to retrieve data from a URL; however, URLs
provide no guarantee of consistency, and may become inaccessible or
change the data the provide. On the other hand, if multiple URLs are
known to provide the same data, they may provide redundant access which
can make up for those limitations.

Lists of URLs for data may be defined in the `urls` directory. If
requested data is not stored locally, any corresponding URLs will be
queried until a match is found: the result will be cached in the `data`
directory and returned.

The bin directory includes several utility scripts to manage the data:
- `key`: Compute the key for the given data.
- `store`: Add data from stdin.
- `add`: Add data from a local file.
- `download`: Add data from a URL, and remember it for future use.
- `learn`: Remember a URL for future use (but don't download it now).
- `get`: Retrieve the specified data, either from cache or a known URL.
- `delete`: Delete the specified data.
- `purge`: Delete all data and any associated URLs.
- `check`: Verify the integrity of all data.
- `clean`: Delete all data which fails verification.
