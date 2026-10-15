def effective_timeout(perform_request_call):
    connection = perform_request_call.args[0]
    timeout = perform_request_call.kwargs.get('timeout')
    return connection.timeout if timeout is None else timeout


def scored_tiers(nested_query):
    tiers = nested_query['nested']['query']['function_score']['query']['dis_max']['queries']
    return [(tier['constant_score']['boost'], tier['constant_score']['filter']) for tier in tiers]


class AttrDict(dict):
    def __init__(self, nested_dict):
        for k, v in nested_dict.items():
            if isinstance(v, dict):
                self[k] = AttrDict(v)
            elif isinstance(v, list):
                self[k] = [
                    AttrDict(e) if isinstance(e, dict) else e for e in v
                ]
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
