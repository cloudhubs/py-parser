import astroid
import astor
import os


class ExitPoint:
    def __init__(self):
        self.name = None
        self.func_name = None
        self.path = None
        self.line_no = None
        self.payload = None
        self.response = None
        self.file_name = None
        self.payload_meta = None
        self.response_meta = None


def process_exit_points(project_path):
    exit_points = list()
    for path, file_name in astor.code_to_ast.find_py_files(project_path):
        file_path = os.path.join(path, file_name)
        exit_points.extend(get_exit_points(file_path))
    return exit_points


def get_exit_points(file_name):
    with open(file_name, "r") as source:
        ast_node = astroid.parse(source.read())

    exit_points = list()

    for node in get_request_statements(ast_node):
        point = ExitPoint()
        print(node.as_string())

        point.name = node.value.func.attrname
        point.file_name = file_name
        point.func_name = find_parent_function(node).name
        point.path = node.value.args[0].value
        point.line_no = node.lineno
        payload = {}
        payload_info = {}
        response = {}
        response_info = {}

        # Try and extract payload
        if len(node.value.args) > 1:
            data = next(node.value.args[1].infer())
            if data:
                attrs = data.instance_attrs
                for key, value in attrs.items():
                    payload[key] = next(attrs[key][-1].infer()).value
                payload_info['name'] = data.name
                payload_info['type'] = data.type
                payload_info['instance_attr'] = list()
                for key, _ in attrs.items():
                    payload_info['instance_attr'].append(key)
                payload_info['funcs'] = list()
                for n in data.get_children():
                    if isinstance(n, astroid.nodes.FunctionDef):
                        payload_info['funcs'].append(n.name)

        # Try and extract response
        if node.targets:
            v = next(node.targets[0].infer())
            if not v == astroid.util.Uninferable:
                response = v

        point.payload = payload
        point.payload_meta = payload_info
        point.response = response
        point.response_meta = response_info

        exit_points.append(point)
    return exit_points


def get_request_statements(root):
    if isinstance(root, astroid.nodes.Assign):
        if check_if_request(root):
            yield root

    if hasattr(root, 'body'):
        for n in root.body:
            yield from get_request_statements(n)


def check_if_request(node):
    if node.is_statement:
        value = node.value
        if hasattr(value, 'func'):
            func = value.func
            return find_request_from_func(func)

    return False


def find_request_from_func(func):
    if hasattr(func, 'expr'):
        return find_request_from_expr(func.expr)


def find_request_from_expr(expr):
    if hasattr(expr, 'name'):
        name = expr.name
        if name == 'requests':
            return True
    if hasattr(expr, 'func'):
        return find_request_from_func(expr.func)

    return False


def find_parent_function(root):
    if isinstance(root.parent, astroid.FunctionDef):
        return root.parent
    else: return find_parent_function(root.parent)
