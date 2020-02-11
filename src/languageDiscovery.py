from src.util import get_files
import os

def getLanguage(file_name):
    if os.path.isfile(file_name):
        return parseFileEnding(file_name)

    else:
        for file in get_files(file_name):
            val = getLanguage(file)
            if val is not None:
                return val
        return None

def parseFileEnding(fileName):
    if fileName.endswith('.py'):
        return 'python'
    if fileName.endswith('.java'):
        return 'java'
    if fileName.endswith('.cpp'):
        return 'C++'
    if fileName.endswith('.c'):
        return 'C'
    if fileName.endswith('.go'):
        return 'Go'
    return None