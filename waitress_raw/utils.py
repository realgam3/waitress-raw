import importlib.util


def import_path(module_file_path):
    spec = importlib.util.spec_from_file_location("waitress_raw_ext", module_file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
