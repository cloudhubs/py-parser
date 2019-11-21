import ast
import inspect
import os
from collections import namedtuple
import importlib
import importlib.util
import os.path
import astor
from astroid import parse


class EntryPoint:
    def __init__(self):
        self.name = None
        self.func_name = None
        self.path = None
        self.payload = None
        self.response = None


class ExitPoint:
    def __init__(self):
        self.name = None
        self.func_name = None
        self.path = None
        self.line_no = None
        self.payload = None
        self.response = None
        self.file_name = None


class Interface:
    def __init__(self, name):
        self.name = name
        self.end_points = list()
        self.exit_points = list()


def system_interfaces(file_name, project_name=None):
    if not project_name:
        project_name = os.path.basename(file_name)

    interface = Interface(project_name)
    process_project(interface, file_name)

    # end_points = get_end_points(file_name)
    # interface.end_points.extend(end_points)

    return interface


def get_imports(root):
    Import = namedtuple("Import", ["module", "name", "alias"])

    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            module = []
        elif isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
        else:
            continue

        for n in node.names:
            for name_ in n.name.split('.'):
                yield Import(module, name_, n.asname)


def get_exit_points(file_name):
    with open(file_name, "r") as source:
        ast_node = parse(source.read())

    points = list()

    # If module does not import the requests module,
    # skip it
    has_requests = False
    request_name = ''

    for imp in get_imports(ast_node):
        if 'requests' in imp.name:
            has_requests = True
            if imp.alias:
                request_name = imp.alias
            else:
                request_name = 'requests'
            break

    if not has_requests:
        return points

    supported_endpoints = ['post', 'get', 'put', 'delete']

    for func_node in ast.walk(ast_node):
        if isinstance(func_node, ast.FunctionDef):
            for node in ast.walk(func_node):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    func = node.func
                    value = func.value
                    if hasattr(value, 'id') and \
                            value.id == request_name and \
                            func.attr in supported_endpoints:

                        point = ExitPoint()
                        point.name = func.attr
                        point.func_name = func_node.name
                        point.path = node.args[0].s
                        point.line_no = node.lineno
                        point.file_name = file_name

                        # for key in node.keywords:
                        #     print('data')
                        #     if key.arg == 'data':
                        #         data = dict()
                        #         for i in range(len(key.value.keys)):
                        #             data[key.value.keys[i].s] = key.value.values[i].s
                        #         point.payload = data
                        #         point.response = find_response(func_node, node)
                        #         break

                        print(astor.dump_tree(node))

                        points.append(point)
    return points


def find_response(func_node, req_node):
    for e_node in ast.walk(func_node):
        if isinstance(req_node, ast.Assign):
            print(ast.dump(e_node))
    return {}


def process_project(system, project_path):
    for path, file_name in astor.code_to_ast.find_py_files(project_path):
        file_path = os.path.join(path, file_name)
        exit_points = get_exit_points(file_path)
        system.exit_points.extend(exit_points)


def format_path(root_path, curr_file):
    curr_file = curr_file.replace('.', '/')
    curr_file = curr_file + '.py'
    return os.path.join(root_path, curr_file)


def get_project_settings(manage_node):
    for node in ast.walk(manage_node):
        if isinstance(node, ast.Call):
            args = node.args
            if len(args) == 2 and args[0].s == 'DJANGO_SETTINGS_MODULE':
                return args[1].s
    raise Exception("Settings configuration not found")


def get_root_conf(setting_node):
    for node in ast.walk(setting_node):
        if isinstance(node, ast.Assign):
            targets = node.targets
            if targets[0].id == 'ROOT_URLCONF':
                return node.value.s
    raise Exception("Root URL configuration not found")


def get_urls(root_url_node, root_package):
    # Process imports
    for node in ast.walk(root_url_node):
        if isinstance(node, ast.Assign):
            targets = node.targets
            if targets[0].id == 'urlpatterns':
                res = []
                for match in node.value.elts:
                    entry_point = EntryPoint()
                    if match.func.id == 'path':
                        entry_point.path = match.args[0].s
                        value = match.args[1]
                        if isinstance(value, ast.Call):
                            pass
                        elif isinstance(value, ast.Name):
                            name = value.id
                            set_entry_details(name, root_url_node, root_package, entry_point)
                        elif isinstance(value, ast.Attribute):
                            func_name = get_func_name_from_attr(value)
                            set_entry_details(func_name, root_url_node, root_package, entry_point)
                        # print(ast.dump(match))

                        res.append(entry_point)
                return res
    raise Exception("URL Patterns configuration not found")


def set_entry_details(name, root_url_node, root_package, entry_point):
    m_import, name = get_import(name, root_url_node)

    if m_import:
        module_func, module_path = get_object_at_import(root_package, m_import, name)
        if module_func:
            entry_point.name = module_path
            entry_point.func_name = module_func.name
            entry_point.payload = module_func.args.args[0].arg


def get_import(name, root_url_node):
    res = None
    for imp in get_imports(root_url_node):
        if imp.alias and imp.alias == name:
            res = imp
            break
        elif imp.name == name:
            res = imp
            break

    if res:
        return res, name
    elif not res:
        new_name_list = name.split('.')[:-1]
        new_name = ".".join(new_name_list)
        if new_name:
            return get_import(new_name, root_url_node)
        else:
            return None, name

    return None, name


def get_func_name_from_attr(node, res=None):
    if res:
        res = node.attr + '.' + res
    else:
        res = node.attr

    if isinstance(node.value, ast.Attribute):
        res = get_func_name_from_attr(node.value, res)

    if isinstance(node.value, ast.Name):
        res = get_func_name_from_name(node.value, res)

    return res


def get_func_name_from_name(node, res=None):
    if res:
        return node.id + '.' + res
    else:
        return node.id


def from_dot_to_dir(root_path, curr_file):
    curr_file = curr_file.replace('.', '/')
    curr_file = curr_file + '.py'
    return os.path.join(root_path, curr_file)


def get_object_at_import(root_package, import_, module_name):
    module_path = from_dot_to_dir(root_package, import_.module)
    spec = importlib.util.spec_from_file_location(import_.module + '.' + module_name, module_path)
    module = importlib.util.module_from_spec(spec)

    if os.path.isfile(module.__file__):
        parsed_node = ast.parse(inspect.getsource(module))
    else:
        return None, module_path

    # Find function
    for node in ast.walk(parsed_node):
        if isinstance(node, ast.FunctionDef) and node.name == module_name:
            return node, module_path

    return None, module_path


def get_end_points(file_path):
    # Find manage.py
    manage = 'manage.py'
    manage = os.path.join(file_path, manage)
    with open(manage, "r") as source:
        tree = ast.parse(source.read())
    setting_path = get_project_settings(tree)

    setting_path = format_path(file_path, setting_path)
    with open(setting_path, "r") as source:
        tree = ast.parse(source.read())
    root_conf = get_root_conf(tree)

    root_conf = format_path(file_path, root_conf)
    with open(root_conf, "r") as source:
        tree = ast.parse(source.read())
    project_url_patterns = get_urls(tree, file_path)

    return project_url_patterns

