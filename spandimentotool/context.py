import pathlib


def projectpath():
    return pathlib.Path(__file__).parents[0]
    # return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))