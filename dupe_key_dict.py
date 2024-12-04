class DupeKeyDict():
    def __init__(self, d=None):
        if d is not None:
            self._keys = list(d.keys())
            self._values = list(d.values())
        else:
            self._keys = []
            self._values = []

    def __setitem__(self, key, value):
        self._keys.append(key)
        self._values.append(value)

    def __delitem__(self, key):
        idx = self._keys.index(key)
        self._keys.pop(idx)
        self._values.pop(idx)

    def __iter__(self):
        return iter(self._keys)

    def update(self, d):
        self._keys.extend(d.keys())
        self._values.extend(d.values())

    def keys(self):
        return self._keys

    def values(self):
        return self._values

    def __repr__(self):
        res = []
        for i in range(len(self._keys)):
            res.append("'{0}': {1}".format(self._keys[i], self._values[i]))
        return '{' + ', '.join(res) + '}'
