class PySystem:
    def __init__(self, name):
        self.name = name
        self.modules = list()
        self.packages = list()
        self.type = 'system'


class PyModule:
    def __init__(self):
        self.name = ''
        self.full_name = ''
        self.relative_name = ''
        self.imports = list()
        self.classes = list()
        self.functions = list()
        self.statements = list()
        self.type = 'module'


class PyPackage:
    def __init__(self):
        self.name = ''
        self.modules = list()
        self.packages = list()
        self.type = 'package'


class PyImport:
    def __init__(self):
        self.name = ''
        self.type = 'import'


class PyClass:
    def __init__(self):
        self.name = ''
        self.imports = list()
        self.bases = list()
        self.classes = list()
        self.functions = list()
        self.statements = list()
        self.component_type = ''
        self.type = 'class'


class PyBase:
    def __init__(self):
        self.id = ''
        self.value = ''
        self.type = 'base_class'


class PyFunction:
    def __init__(self):
        self.name = ''
        self.args = list()
        self.imports = list()
        self.classes = list()
        self.functions = list()
        self.statements = list()
        self.component_type = ''
        self.type = 'function'


class PyCall:
    def __init__(self):
        self.statement_type = 'function_call'
        self.func = ''
        self.args = list()
        self.keywords = list()
        self.type = 'statement_function_call'


class PyName:
    def __init__(self):
        self.statement_type = ''
        self.name = ''
        self.type = 'statement_assign'


class PyArgCall:
    def __init__(self):
        self.statements = list()
        self.type = 'arg_call'
