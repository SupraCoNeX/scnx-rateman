from importlib import import_module

def load(rc_alg):
    return import_module(rc_alg).start
