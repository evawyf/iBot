
class BiDict(dict):
    def __init__(self, *args, **kwargs):
        super(BiDict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(BiDict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key], []).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(BiDict, self).__delitem__(key)

    def get_key(self, value):
        return self.inverse.get(value, [None])[0]
    

if __name__ == "__main__":

    # Create a BiDict
    bd = BiDict({'a': 1, 'b': 2, 'c': 3})

    # Use it like a regular dict
    print(bd['a'])  # Output: 1

    # Look up a key by value
    print(bd.get_key(2))  # Output: 'b'

    # Add a new key-value pair
    bd['d'] = 4

    # Look up the new key by value
    print(bd.get_key(4))  # Output: 'd'

    # Update the BiDict
    bd.update({'e': 6, 'f': 7})
    print(bd)

    bd.update({'f': 777})   # Output: {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 6, 'f': 7}
    print(bd)
    print(bd.get_key(777))  # Output: {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 6, 'f': 777}

    # Remove a key-value pair
    del bd['c']
    print(bd)  # Output: {'a': 1, 'b': 2, 'd': 4, 'e': 6, 'f': 777}
    print(bd.get_key(3))  # Output: None

    # Try to remove a non-existent key
    try:
        del bd['z']
    except KeyError:
        print("Key 'z' not found in the BiDict")

