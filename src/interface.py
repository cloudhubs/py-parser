import ast
import os
from collections import namedtuple


class EndPoint:
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
    if os.path.isdir(file_name):
        if not project_name:
            project_name = os.path.basename(file_name)

        interface = Interface(project_name)
        process_directory(interface, file_name, file_name)
        return interface
    else:
        return None


def get_end_points(ast_node):
    points = list()

    for node in ast.walk(ast_node):
        if isinstance(node, ast.FunctionDef):
            if 'request' in node.args:
                point = EndPoint()
                point.name = node.name
                point.func_name = node.name
                points.append(point)

    return points


def get_imports(root):
    Import = namedtuple("Import", ["module", "name", "alias"])

    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            module = []
        elif isinstance(node, ast.ImportFrom) and node.module:
            module = node.module.split('.')
        else:
            continue

        for n in node.names:
            yield Import(module, n.name.split('.'), n.asname)


def get_exit_points(ast_node, file_name):
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

                        for key in node.keywords:
                            if key.arg == 'data':
                                data = dict()
                                for i in range(len(key.value.keys)):
                                    data[key.value.keys[i].s] = key.value.values[i].s
                                point.payload = data

                        points.append(point)

    return points


def process_regular_file(file_name, system):
    if not file_name.endswith('.py'):
        return None

    with open(file_name, "r") as source:
        tree = ast.parse(source.read())

    # end_points = get_end_points(tree)
    exit_points = get_exit_points(tree, file_name)

    # system.end_points.extend(end_points)
    system.exit_points.extend(exit_points)


def process_directory(app_node, root_name, file_path):
    for file in os.listdir(file_path):
        full_name = os.path.join(file_path, file)

        if os.path.isfile(full_name) and file.endswith('.py'):
            process_regular_file(full_name, app_node)

        elif os.path.isdir(full_name):
            process_directory(app_node, root_name, full_name)

    return app_node
