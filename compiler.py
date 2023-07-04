from pathlib import Path

from anytree import RenderTree

from lexer import Lexer
from parser_ import Parser, get_grammar


def main():
    lexer = Lexer(Path("input.txt"))
    parser = Parser(lexer)
    parse_tree, errors = parser.parse()
    with open("parse_tree.txt", "w") as f:
        f.write(RenderTree(parse_tree.to_anytree()).by_attr())
    with open("syntax_errors.txt", "w") as f:
        if len(errors) == 0:
            f.write(f"There is no syntax error.")
        else:
            for error in errors:
                f.write(f"{error}\n")


if __name__ == "__main__":
    main()
