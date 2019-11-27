import ntpath


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
