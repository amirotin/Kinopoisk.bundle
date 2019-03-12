import sys
import os


def init_lib_path(core):
    shared_path = os.path.join(core.bundle_path, 'Contents', 'Libraries', 'Shared')
    for lib in os.listdir(shared_path):
        lib_path = os.path.join(shared_path, lib)
        if os.path.isdir(lib_path) and lib_path not in sys.path:
            sys.path.append(lib_path)


def restore_builtins(module, base):
    module.__builtins__ = [x for x in base.__class__.__base__.__subclasses__() if x.__name__ == 'catch_warnings'][0]()._module.__builtins__