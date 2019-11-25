import ast
import inspect
import os
from collections import namedtuple
import importlib
import importlib.util
import os.path
import astor
import astroid
import glob


class EntryPoint:
    def __init__(self):
        self.name = None
        self.func_name = None
        self.path = None
        self.payload = None
        self.payload_meta = None
        self.response_meta = None
        self.response = None
        self.line_no = None
        self.decorators = list()


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
    exit_points = process_exit_points(file_name)
    end_points = get_end_points(file_name)
    interface.exit_points.extend(exit_points)
    interface.end_points.extend(end_points)
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


def check_if_request(node):
    if node.is_statement:
        value = node.value
        if hasattr(value, 'func'):
            func = value.func
            if hasattr(func, 'expr'):
                expr = func.expr
                if hasattr(expr, 'name'):
                    name = expr.name
                    if name == 'requests':
                        return True
    return False


def get_request_statements(root):
    if isinstance(root, astroid.nodes.Assign):
        if check_if_request(root):
            yield root

    for n in root.get_children():
        yield from get_request_statements(n)


def get_exit_points(file_name):
    with open(file_name, "r") as source:
        ast_node = astroid.parse(source.read())

    exit_points = list()

    for node in get_request_statements(ast_node):
        point = ExitPoint()
        point.name = node.value.func.attrname
        point.file_name = file_name
        point.func_name = node.parent.name
        point.path = node.value.args[0].value
        point.line_no = node.lineno
        payload = {}
        response = {}

        # Try and extract payload
        if len(node.value.args) > 1:
            data = next(node.value.args[1].infer())
            if data:
                attrs = data.instance_attrs
                for key, value in attrs.items():
                    payload[key] = next(attrs[key][-1].infer()).value

        # Try and extract response
        if node.targets:
            v = next(node.targets[0].infer())
            if not v == astroid.util.Uninferable:
                response = v

        point.payload = payload
        point.response = response
        exit_points.append(point)
    return exit_points


def process_exit_points(project_path):
    exit_points = list()
    for path, file_name in astor.code_to_ast.find_py_files(project_path):
        file_path = os.path.join(path, file_name)
        exit_points.extend(get_exit_points(file_path))
    return exit_points


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


def get_view_at_import(root_package, module_name, level, func_name):
    view_path = os.path.join(root_package, '.' * level + '/' + module_name + '.py')
    view_path = os.path.normpath(view_path)
    with open(view_path, "r") as source:
        ast_node = astroid.parse(source.read())
    return ast_node.lookup(func_name)[1][0], view_path


def check_if_urlpatterns(node):
    if node.is_statement:
        targets = node.targets
        if targets:
            target = targets[0]
            if hasattr(target, 'name') and target.name == 'urlpatterns':
                return True
    return False


def get_url_statements(root):
    for n in root.get_children():
        if isinstance(n, astroid.nodes.Assign):
            if check_if_urlpatterns(n):
                yield n


def process_file_for_url_patterns(root_file, file_name):
    end_points = list()

    with open(file_name, "r") as source:
        ast_node = astroid.parse(source.read())
        # use ilookup('urlpatterns')
        for node in get_url_statements(ast_node):
            # print(node.repr_tree())
            for pattern in node.value.elts:
                end_point = EntryPoint()
                path = next(pattern.args[0].infer()).value
                end_point.path = path
                # end_point.func_name = pattern

                name = None
                if pattern.keywords:
                    name = next(pattern.keywords[0].value.infer()).value

                view = pattern.args[1]
                add_node = False
                if isinstance(view, astroid.Attribute):
                    add_node = True
                    if not name:
                        name = view.attrname
                    end_point.name = name

                    view_el = view.expr.name
                    imp = ast_node.lookup(view_el)[1][0]

                    view_func, file_ = get_view_at_import(root_file, imp.names[0][0], imp.level, view.attrname)
                    end_point.line_no = view_func.lineno
                    end_point.name = view_func.name
                    end_point.func_name = file_

                    payloads = list()
                    for arg in view_func.args.args:
                        payload = dict()
                        arg_name = arg.name
                        payload['name'] = arg_name

                        payloads.append(payload)

                    end_point.payload = payloads

                    response = {}
                    end_point.response = response

                    # Decorators
                    if view_func.decorators:
                        decs = view_func.decorators.nodes
                        for n in decs:
                            end_point.decorators.append(n.name)

                if add_node:
                    end_points.append(end_point)

    return end_points


def get_end_points(file_path):
    file_paths = os.path.join(file_path, '*.py')
    end_points = list()

    for file in glob.iglob(file_paths):
        end_points.extend(process_file_for_url_patterns(file_path, file))

    return end_points

    # # Find manage.py
    # manage = 'manage.py'
    # manage = os.path.join(file_path, manage)
    # with open(manage, "r") as source:
    #     tree = ast.parse(source.read())
    # setting_path = get_project_settings(tree)
    #
    # setting_path = format_path(file_path, setting_path)
    # with open(setting_path, "r") as source:
    #     tree = ast.parse(source.read())
    # root_conf = get_root_conf(tree)
    #
    # root_conf = format_path(file_path, root_conf)
    # with open(root_conf, "r") as source:
    #     tree = ast.parse(source.read())
    # project_url_patterns = get_urls(tree, file_path)
    #
    # return project_url_patterns
