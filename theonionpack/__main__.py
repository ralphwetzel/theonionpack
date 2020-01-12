#!/usr/bin/env python
import importlib
import pathlib
import site


def main():

    # Per definition, __main__.__file__ is the only __file__, that could carry a relative path!
    # => https://docs.python.org/3.4/whatsnew/3.4.html#other-language-changes
    # So we resolve it here!
    path = pathlib.Path(__file__).resolve()

    # If run as 'python -m xy', '.' is not part of sys.path.
    # __package__ as well is either '' or None.
    # Therefore any import from our package fails.
    # Solution: Add the path of __main__.py (this file) to sys.path
    if __name__ == '__main__' and __package__ in ['', None]:
        site.addsitedir(str(path.parent))
        from theonionpack import main as packmain
    else:
        from .theonionpack import main as packmain

    packmain()


if __name__ == '__main__':
    main()
