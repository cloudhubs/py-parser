import os
import os.path
import ntpath
from .exit_points import process_exit_points
from .entry_points import get_end_points


class System:
    def __init__(self):
        self.name = ''
        self.interfaces = list()


class Interface:
    def __init__(self, name):
        self.name = name
        self.end_points = list()
        self.exit_points = list()


def get_services(project_path):
    for name in os.listdir(project_path):
        if not name.startswith('.'):
            name = os.path.join(project_path, name)
            if os.path.isdir(name):
                yield name


def system_interfaces(file_name, project_name=None):
    if not project_name:
        project_name = path_leaf(file_name)

    #  get services
    system = System()
    system.name = project_name

    for service in get_services(file_name):
        interface = Interface(path_leaf(service))

        exit_points = process_exit_points(service)
        end_points = get_end_points(service)

        interface.exit_points.extend(exit_points)
        interface.end_points.extend(end_points)

        system.interfaces.append(interface)

    return system


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)
