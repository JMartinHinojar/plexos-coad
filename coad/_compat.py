import types


import sys

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)


if not is_py2:
    def cmp(a, b):
        return (a > b) - ( a < b )
else:
    cmp = cmp
