import astroid
import os
from src.util import ast_walk, path_base
from src.nodes import Point, Payload


def get_project_settings(tree):
    for node in ast_walk(tree):
        if isinstance(node, astroid.Name) and node.name == 'os':
            env_node = node.parent
            if env_node and isinstance(env_node, astroid.Attribute) and env_node.attrname == 'environ':
                set_default = env_node.parent
                if set_default and isinstance(set_default, astroid.Attribute) and set_default.attrname == 'setdefault':
                    setting = node.statement()
                    return next(setting.value.args[1].infer()).value
    return None


def get_root_conf(tree):
    for node in ast_walk(tree):
        if isinstance(node, astroid.Assign):
            target = node.targets[0]
            if target.name == 'ROOT_URLCONF':
                return node.value.value
    return None


def get_end_points(file_path):
    manage = 'manage.py'
    manage = os.path.join(file_path, manage)
    with open(manage, "r") as source:
        tree = astroid.parse(source.read())
    setting_path = get_project_settings(tree)

    setting_path = format_path(file_path, setting_path)
    with open(setting_path, "r") as source:
        tree = astroid.parse(source.read())
    root_conf = get_root_conf(tree)

    root_conf = format_path(file_path, root_conf)
    with open(root_conf, "r") as source:
        tree = astroid.parse(source.read())
    url_patterns = tree.lookup('urlpatterns')
    url_patterns = url_patterns[1][0].statement()
    return process_file_for_url_patterns(tree, path_base(root_conf), url_patterns.value)


def format_path(root_path, curr_file):
    curr_file = curr_file.replace('.', '/')
    curr_file = curr_file + '.py'
    return os.path.join(root_path, curr_file)


def process_file_for_url_patterns(ast_node, root_file, patterns):
    end_points = list()

    for pattern in patterns.elts:
        end_point = Point()
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

            for arg in view_func.args.args:
                arg_name = arg.name
                end_point.payload.append(arg_name)

            response = Payload()
            end_point.response = response

            # Decorators
            if view_func.decorators:
                decs = view_func.decorators.nodes
                for n in decs:
                    if isinstance(n, astroid.Name):
                        end_point.decorators.append(n.name)
                    elif isinstance(n, astroid.Call):
                        d = dict()
                        d['name'] = n.func.name
                        for key in n.keywords:
                            d[key.arg] = list()
                            for v in key.value.elts:
                                d[key.arg].append(v.value)
                        end_point.decorators.append(d)

        if add_node:
            end_points.append(end_point)

    return end_points


def get_url_statements(root):
    for n in root.get_children():
        if isinstance(n, astroid.nodes.Assign):
            if check_if_urlpatterns(n):
                yield n


def check_if_urlpatterns(node):
    if node.is_statement:
        targets = node.targets
        if targets:
            target = targets[0]
            if hasattr(target, 'name') and target.name == 'urlpatterns':
                return True
    return False


def get_view_at_import(root_package, module_name, level, func_name):
    view_path = os.path.join(root_package, '.' * level + '/' + module_name + '.py')
    view_path = os.path.normpath(view_path)
    with open(view_path, "r") as source:
        ast_node = astroid.parse(source.read())
    return ast_node.lookup(func_name)[1][0], view_path
