import os
import os.path
from src.exit_points import process_exit_points
from src.entry_points import get_end_points
from src.util import path_leaf
from src.nodes import System, Interface


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

