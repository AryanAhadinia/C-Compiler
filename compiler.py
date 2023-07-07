### Arshan Dalili: 98105751
### Aryan Ahadinia: 98103878

from pathlib import Path

from anytree import RenderTree

from lexer import Lexer
from transition_diagram_parser import Parser


def main():
    lexer = Lexer(Path("input.txt"))
    parser = Parser(lexer)
    parse_tree, errors = parser.parse()
    parser.code_generator.to_code_string("output.txt")
    with open("parse_tree.txt", "w") as f:
        f.write(RenderTree(parse_tree.to_anytree()).by_attr())


if __name__ == "__main__":
    main()
