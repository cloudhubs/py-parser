import astroid

from pylint import checkers
from pylint import interfaces


class UselessReturnChecker():

    def visit_functiondef(self, node):
        """
            Checks for presence of return statement at the end of a function
            "return" or "return None" are useless because None is the default
            return type if they are missing
        """
        # if the function has empty body then return
        if not node.body:
            return

        last = node.body[-1]
        if isinstance(last, astroid.Return):
            # e.g. "return"
            if last.value is None:
                self.add_message('useless-return', node=node)
            # e.g. "return None"
            elif isinstance(last.value, astroid.Const) and (last.value.value is None):
                self.add_message('useless-return', node=node)


analyzer = UselessReturnChecker()
analyzer.