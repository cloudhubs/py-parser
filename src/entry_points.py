import astroid
import os
from src.util import ast_walk, path_base, decipher_props
from src.nodes import Point, Payload


def get_project_settings(tree):
    # Helper function to retrieve project's settings file
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
    # Helper function to retrieve application roof url config
    for node in ast_walk(tree):
        if isinstance(node, astroid.Assign):
            target = node.targets[0]
            if target.name == 'ROOT_URLCONF':
                return node.value.value
    return None


def get_end_points(file_path):
    # Retrieve app's manage.py file which contains config for
    # the oath for the app's settings module
    manage = 'manage.py'
    manage = os.path.join(file_path, manage)

    with open(manage, "r") as source:
        tree = astroid.parse(source.read())
    # Retrieve settings path
    setting_path = get_project_settings(tree)

    # Reformat settings path from dot structure to directory structure
    # Use settings module to retrieve path to application's url config
    setting_path = format_path(file_path, setting_path)
    with open(setting_path, "r") as source:
        tree = astroid.parse(source.read())
    # Get app url config
    root_conf = get_root_conf(tree)

    # Reformat from dot to dir
    # Retrieve project url module and get all the rest end-points
    root_conf = format_path(file_path, root_conf)
    with open(root_conf, "r") as source:
        tree = astroid.parse(source.read())
    url_patterns = tree.lookup('urlpatterns')
    url_patterns = url_patterns[1][0].statement()

    # Process app rest end-points for the views and url
    return process_file_for_url_patterns(tree, path_base(root_conf), url_patterns.value)


def format_path(root_path, curr_file):
    # Converts a dot structure to a directory structure
    # Eg. abc.edu => abc/edu
    curr_file = curr_file.replace('.', '/')
    curr_file = curr_file + '.py'
    return os.path.join(root_path, curr_file)


def process_file_for_url_patterns(ast_node, root_file, patterns):
    # Take a set of url patterns and retrieves the various properties for the
    # rest end-points
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

            view_func, file_path = get_view_at_import(root_file, imp.names[0][0], imp.level, view.attrname)
            end_point.line_no = view_func.lineno
            end_point.name = view_func.name
            end_point.func_name = view_func.name
            end_point.file_name = file_path

            arg = view_func.args.args[0]
            # end_point.payload.name = arg.name
            end_point.payload = decipher_props(view_func, arg.name)

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
