import ntpath
import os


def ast_walk(root):
    yield root
    for node in root.get_children():
        yield from ast_walk(node)


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def path_base(path):
    head, tail = ntpath.split(path)
    return head

def get_services(project_path):
    for name in os.listdir(project_path):
        if not name.startswith('.'):
            name = os.path.join(project_path, name)
            if os.path.isdir(name):
                yield name