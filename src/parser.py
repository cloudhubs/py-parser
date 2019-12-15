import ast
import os
import tempfile
from enum import Enum
from urllib.parse import urlparse
from src.nodes import *
from src.util import path_leaf, get_services


class NodeType(Enum):
    IMPORTS = 'imports'
    CLASSES = 'classes'
    FUNCTIONS = 'functions'
    STATEMENTS = 'statements'


class ComponentType(Enum):
    VIEW = 'view'
    TEMPLATE = 'template'
    SERVICE = 'service'
    MODEL = 'model'
    MIGRATION = 'migration'
    TEST = 'test'
    CONFIG = 'config'
    GENERIC = 'generic'


def parse_source_file(file_name):
    # If url, process url first
    # if urlparse(file_name).scheme in ('http', 'https'):
    #     return process_url(file_name)

    # if file path determine if single file or directory
    if os.path.isfile(file_name):
        return process_regular_file(file_name)

    # if directory go through all files recursively
    if os.path.isdir(file_name):
        project_name = path_leaf(file_name)
        system = PySystem(project_name)
        # TODO get all apps and loop for each app
        for service in get_services(file_name):
            py_app = PyApp(path_leaf(service))
            system.apps.append(process_directory(py_app, service, service))
        return system


# def process_url(git_url):
#     # Download the project locally
#     with tempfile.TemporaryDirectory() as temp_dirname:
#         Repo.clone_from(git_url, temp_dirname)
#         # Run analysis
#         return parse_source_file(temp_dirname, git_url.rsplit('/', 1)[-1])


def process_regular_file(file_name):
    if not file_name.endswith('.py'):
        return None

    with open(file_name, "r") as source:
        tree = ast.parse(source.read())

    module = PyModule()
    return parse_node(tree, module)


def process_directory(app_node, root_name, file_path):
    for file in os.listdir(file_path):
        full_name = os.path.join(file_path, file)
        simple_name = os.path.relpath(full_name, root_name)
        short_name = file

        if os.path.isfile(full_name) and file.endswith('.py'):
            module_node = process_regular_file(full_name)
            module_node.name = short_name
            module_node.relative_name = simple_name
            module_node.full_name = full_name
            app_node.modules.append(module_node)

        elif os.path.isdir(full_name):
            package_node = PyPackage()

            # TODO: Ignore some files, may be using project's git ignore
            # if simple_name not in files_to_ignore:

            process_directory(package_node, root_name, full_name)
            package_node.name = short_name
            package_node.relative_name = simple_name
            package_node.full_name = full_name
            app_node.packages.append(package_node)

    return app_node


def raw_source_file(file_name):
    with open(file_name, "r") as source:
        tree = ast.parse(source.read())
    tree.name = 'app'
    return tree


def parse_node(ast_node, node):
    analyzer = Analyzer(node)
    analyzer.visit(ast_node)
    return analyzer.module


def set_class_component_type(node):
    for base in node.bases:
        base_id = base.name
        base_value = base.value

        if base_id == 'migrations':
            node.component_type = 'migration'
        elif base_id == 'models':
            node.component_type = 'model'
        elif base_id == 'TestCase':
            node.component_type = 'test'
        elif base_id == 'AppConfig':
            node.component_type = 'config'
        elif base_id == 'admin' and base_value == 'ModelAdmin':
            node.component_type = 'model'

    if not node.component_type:
        node.component_type = 'generic'


def set_func_component_type(node):
    for arg in node.args:
        if arg == 'self':
            continue
        elif arg == 'request':
            node.component_type = 'view'

    if not node.component_type:
        node.component_type = 'generic'


class Analyzer(ast.NodeVisitor):
    def __init__(self, module):
        self.module = module

    def visit_Import(self, ast_node):
        print(self.module.name)
        for alias in ast_node.names:
            imp = PyImport()
            imp.name = alias.name
            self.module.imports.append(imp)

    def visit_ImportFrom(self, ast_node):
        for alias in ast_node.names:
            imp = PyImport()
            imp.name = alias.name
            self.module.imports.append(imp)

    def visit_ClassDef(self, ast_node):
        node = PyClass()
        node.name = ast_node.name

        for base in ast_node.bases:
            base_node = PyBase()

            if isinstance(base, ast.Name):
                base_node.name = base.id
            elif isinstance(base, ast.Attribute):
                base_node.name = base.value.id
                base_node.value = base.attr

            node.bases.append(base_node)

        for ast_child_node in ast_node.body:
            parse_node(ast_child_node, node)

        set_class_component_type(node)
        self.module.classes.append(node)

    def visit_FunctionDef(self, ast_node):
        node = PyFunction()
        node.name = ast_node.name

        for arg in ast_node.args.args:
            node.args.append(arg.arg)

        # node['returns'] = ast_node.returns

        for ast_child_node in ast_node.body:
            parse_node(ast_child_node, node)

        set_func_component_type(node)
        self.module.functions.append(node)

    def visit_Call(self, ast_node):
        node = PyCall()
        func = ast_node.func

        if isinstance(func, ast.Name):
            node.func = func.id
        elif isinstance(func, ast.Attribute):
            node.func = func.attr

        for arg in ast_node.args:
            if isinstance(arg, ast.Name):
                node.args.append(arg.id)
            elif isinstance(arg, ast.Call):
                call_dict = PyArgCall()
                parse_node(arg, call_dict)
                node.args.append(call_dict)
            elif isinstance(arg, ast.Num):
                node.args.append(arg.n)
            elif isinstance(arg, ast.Str):
                node.args.append(arg.s)

        for keyword in ast_node.keywords:
            node.keywords.append(keyword.arg)

        self.module.statements.append(node)

    def visit_Name(self, ast_node):
        node = PyName()
        node.name = ast_node.id

        ctx = ast_node.ctx
        if isinstance(ctx, ast.Load):
            node.statement_type = 'Load'
        elif isinstance(ctx, ast.Store):
            node.statement_type = 'Store'
        elif isinstance(ctx, ast.Del):
            node.statement_type = 'Del'

        self.module.statements.append(node)
