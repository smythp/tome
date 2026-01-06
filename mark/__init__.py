"""mark - Position and session state tracking.

Tracks where you are in hierarchical data and provides navigation.

Basic usage:
    from mark import Mark

    mark = Mark(store=my_store)
    mark.into(5).into(10)  # navigate into buffers
    mark.back()            # return to previous
    mark.reset()           # return to root
    mark.path              # ['root', 'projects', 'tome']
"""

from .mark import Mark

__all__ = ["Mark"]
