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

TODO: update ^


## y tho

We're very familiar with "location addressable storage" (e.g., "the data available at a particular URL"), and have robust tooling for transferring data between locations (e.g., web browsers, curl); but we're *so* familiar with it that we frequently conflate it with other concepts, which bear superficial resemblance but in fact are fundamentally orthogonal.

In particular, dependency management and provisioning tools attempt to solve the problem "I want to deploy and run some code, and I know exactly what other code it depends on in order to run; now, how do I get it all installed and actually running on another computer?", and their usual solution is essentially "retrieve and execute code from each of these URLs". This approach has a number of issues, but we find ways to work around them: a specific URL might be temporarily unavailable, but we can construct a list of fallback URLs; the data at a URL might change or become corrupted in transit, but we can compute a cryptographic hash of the data we downloaded and make sure it matches its unique expected value; etc.

In reality, most systems don't account for these issues, and those that do increase tremendously in complexity and develop new issues as a result -- and *none* of them are capable of handling the case of "I need to rebuild this Docker image, but the wifi is down".

`What if I told you` that these issues all stem from a common foundational and fixable cause: that the procedure above is *exactly backwards* from what it should be?

If you already know a cryptographic hash of some data, it doesn't matter where or how you acquire the actual data: just *somehow* get it from *somewhere* (even a totally untrusted server, over an insecure connection!), compute its hash, and make sure it matches what you expected. If so, you're done; if not, try somewhere else: you might already have it on your own filesystem; or you can ask someone else if they have it, or if they know where else to look.

In general, if you already know exactly how to *recognize* the data you're looking for, location addressable storage is just one potential component of a *content* addressable storage system, and whole new worlds of possibilities open up. For example, maybe a tracking service can give you a list of known purveyors of the particular data you're looking for, along with their reputation scores for speed and accuracy. You can then select a handful of them based on their reputation; ask each of them to give you a specific portion of the data simultaneously; download and verify the integrity of both each portion and the whole; and suddenly you've created BitTorrent.

BitTorrent is an amazing technology, and is sometimes used for provisioning, but not (as far as I can tell) for dependency management: probably because it is pretty complex, and not installed by default on most computers -- in contrast with existing solutions, which work out of the box and are *usually* "good enough".

Stuff is not a BitTorrent client, and does not implement most of its features; but it *is* a working content addressable storage system in a single bash script, whose only external dependencies come pre-installed in nearly every flavor of Linux or Mac. So something not entirely unlike it *might* revolutionize the way we do dependency management.

Thanks for coming to my Fred Talk.


## See also

- Joe Armstrong: ["The Mess We're In"](https://www.youtube.com/watch?v=lKXe3HUG2l4)
- Gary Bernhardt: ["A Whole New World"](https://www.destroyallsoftware.com/talks/a-whole-new-world)
- Tim Berners-Lee: ["Cool URIs don't change"](https://www.w3.org/Provider/Style/URI)
- Nix: [an immutable, functional package manager](https://nixos.org/nix/)
- Unison: [a content-addressable programming language](http://unisonweb.org)
