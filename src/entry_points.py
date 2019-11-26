import astroid
import os
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
