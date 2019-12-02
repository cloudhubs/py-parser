import astroid
import astor
import os
from src.util import ast_walk
from src.nodes import Point, Payload


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

    for node in find_request_from_walk(ast_node):
        point = Point()
        scope_func = node.scope()
        statement = find_statement_node(node)

        if isinstance(statement, astroid.Assign):
            response = statement.targets[0]
            request = statement.value
            process_request(request, point)
            process_response(response, point)
        elif isinstance(statement, astroid.Expr):
            request = statement.value
            process_request(request, point)

        point.file_name = file_name
        point.func_name = scope_func.name
        point.line_no = node.lineno

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


def find_request_from_walk(root):
    for node in ast_walk(root):
        if hasattr(node, 'name'):
            name = node.name
            if name == 'requests':
                yield node


def find_parent_function(root):
    if isinstance(root.parent, astroid.FunctionDef):
        return root.parent
    else:
        return find_parent_function(root.parent)


def find_statement_node(expr):
    state = expr
    while not state.is_statement and hasattr(state, 'parent'):
        state = state.parent
    return state


request_types = ['get', 'post', 'delete', 'put']


def find_rest_call_node(node):
    res = node
    if res.func.attrname in request_types:
        return res, res.func.attrname
    else:
        return find_rest_call_node(res.func.expr)


def process_request(expr_node, result):
    payload_meta = Payload()
    url = ''

    call_node, request_type = find_rest_call_node(expr_node)
    request_args = call_node.args
    url_node = request_args[0]

    if hasattr(url_node, 'value'):
        url = url_node.value
    elif isinstance(url_node, astroid.BinOp):
        url = ''
        url += get_node_value(url_node.left)
        url += get_node_value(url_node.right)

    has_payload = len(request_args) > 1

    payload_node = None
    if has_payload:
        payload_node = request_args[1]

    if not has_payload and call_node.keywords:
        for keyword in call_node.keywords:
            if keyword.arg == 'data':
                payload_node = keyword.value

    if payload_node:
        if isinstance(payload_node, astroid.Dict):
            payload_meta.type = payload_node.pytype()
            payload_meta.name = '_dict'

            for key, value in payload_node.items:
                key = next(key.infer()).value
                payload_meta.props.append(key)

    result.name = request_type
    result.payload.append(payload_meta)
    result.path = url


def get_node_value(node):
    if hasattr(node, 'value'):
        return node.value
    return ''


def process_response(response_node, result):
    response_meta = Payload()
    result.response = response_meta
