from flask import Flask
from flask import request
import ast
import jsonpickle


app = Flask(__name__)


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )
    cls.__str__ = __str__
    cls.__repr__ = __str__
    return cls


def parse_source_code(file_name):
    with open(file_name, "r") as source:
        tree = ast.parse(source.read())
    tree.name = 'app'
    module = parse_tree(tree, 'module')
    return jsonpickle.encode(module, unpicklable=False)


def parse_tree(tree, node_type):
    ast.dump(tree)
    name = ''
    if hasattr(tree, 'name'):
        name = tree.name
    analyzer = Analyzer(name, node_type)
    analyzer.visit(tree)
    return analyzer.module


def parse_children(parent_node, tree):
    for node in tree.body:
        print(ast.dump(node))
        if isinstance(node, ast.FunctionDef):
            analyzer = Analyzer(node.name, 'function')
            analyzer.visit(node)
            parent_node.functions.append(analyzer.module)
        elif isinstance(node, ast.ClassDef):
            analyzer = Analyzer(node.name, 'class')
            analyzer.visit(node)
            parent_node.classes.append(analyzer.module)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                parent_node.imports.append(alias.name)
        elif isinstance(node, ast.Expr):
            analyzer = Analyzer(node.value, 'statement')
            analyzer.visit(node)
            # parent_node.statements.append(analyzer.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
            else:
                name = node.func.value
            analyzer = Analyzer(name, 'statement')
            analyzer.visit(node)
            parent_node.statements.append(analyzer.module)
        else:
            print("Not Defined")
            parent_node.statements.append(node)


class Analyzer(ast.NodeVisitor):
    def __init__(self, name):
        self.module = PyNode(name)

    def visit_Import(self, node):
        for alias in node.names:
            self.module.imports.append(alias.name)
            self.module.node_type = 'import'

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.module.imports.append(alias.name)
            self.module.node_type = 'import'

    def visit_Expr(self, node):
        state_node = PyExpression(node.value)
        self.module.statements.append(state_node)
        self.module.node_type = 'statement'

    def visit_Call(self, node):
        _node = PyFuncCallExpr(node)
        self.module.statements.append(_node)
        self.module.node_type = 'statement'

    def visit_FunctionDef(self, node):
        _node = PyNode(node.name, 'function')
        parse_children(_node, node)
        self.module.functions.append(_node)

    def visit_ClassDef(self, node):
        _node = PyNode(node.name, 'class')
        parse_children(_node, node)
        self.module.classes.append(_node)

    # def visit_If(self, node):
    #     _node = PyNode(node, 'statement')
    #     parse_children(_node, node)
    #     self.module.statements.append(_node)
    #
    # def visit_Assign(self, node):
    #     _node = PyNode(node, 'statement')
    #     self.module.statements.append(_node)


@auto_str
class PyNode:

    def __init__(self, name, node_type):
        self.name = name
        self.node_type = node_type
        self.imports = []
        self.classes = []
        self.functions = []
        self.statements = []


@auto_str
class PyClass:

    def __init__(self):
        self.name = ''
        self.methods = []
        self.statements = []


@auto_str
class PyFunction:
    def __init__(self):
        self.name = ''
        self.expressions = []


@auto_str
class PyExpression:
    def __init__(self, expr):
        self.expr = expr
        self.type = 'simple_statement'


@auto_str
class PyFuncCallExpr:
    def __init__(self, expr):
        self.func = expr.func
        self.args = expr.args
        self.keywords = expr.keywords
        self.type = 'function_call'


def remove_empty_elements(d):
    print("Enter")
    """recursively remove empty lists, empty dicts, or None elements from a dictionary"""
    def empty(x):
        return x is None or x == {} or x == []

    if not isinstance(d, (dict, list)):
        return d
    elif isinstance(d, list):
        return [v for v in (remove_empty_elements(v) for v in d) if not empty(v)]
    else:
        print("Here")
        return {k: v for k, v in ((k, remove_empty_elements(v)) for k, v in d.items()) if not empty(v)}


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/parse', methods=['POST'])
def parser():
    request_data = request.get_json()
    return parse_source_code(request_data['fileName'])


if __name__ == '__main__':
    app.run()
