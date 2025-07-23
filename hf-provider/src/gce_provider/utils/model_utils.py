from types import SimpleNamespace


def to_simple_namespace(data):
    """Convert data into SimpleNamespace objects"""
    if type(data) is list:
        return list(map(to_simple_namespace, data))
    elif type(data) is dict:
        sns = SimpleNamespace()
        for key, value in data.items():
            setattr(sns, key, to_simple_namespace(value))
        return sns
    else:
        return data
