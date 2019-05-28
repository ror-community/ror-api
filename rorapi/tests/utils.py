class AttrDict(dict):

    def __init__(self, nested_dict):
        for k, v in nested_dict.items():
            if isinstance(v, dict):
                self[k] = AttrDict(v)
            elif isinstance(v, list):
                self[k] = [AttrDict(e) if isinstance(e, dict) else e
                           for e in v]
            else:
                self[k] = v

    def __getattr__(self, attr):
        if attr not in self:
            raise AttributeError(
                '\'AttrDict\' object has no attribute \'{}\''.format(attr))
        return self[attr]


class IterableAttrDict():

    def __init__(self, nested_dict, iter_list):
        self.attr_dict = AttrDict(nested_dict)
        self.iter_list = [AttrDict(i) for i in iter_list]

    def __iter__(self):
        return iter(self.iter_list)

    def __getitem__(self, key):
        return self.iter_list[key]

    def __getattr__(self, attr):
        return self.attr_dict.__getattr__(attr)
