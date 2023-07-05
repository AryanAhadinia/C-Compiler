from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set

from anytree import Node, RenderTree

from lexer import Lexer, Token, TokenType
from code_gen import CodeGenerator

EPSILON = "EPSILON"


class Production(object):
    def __init__(self, lhs: str, rhs: List[List[str]]):
        self.lhs = lhs
        self.rhs = rhs

    def has_epsilon(self):
        for rhs in self.rhs:
            if len(rhs) == 1 and rhs[0] == EPSILON:
                return True
        return False


class Grammar(object):
    def __init__(
        self,
        productions: List[Production],
        start_symbol: str,
        terminals: List[str],
        non_terminals: List[str],
        actions: List[str],
        firsts: Dict[str, Set[str]],
        follows: Dict[str, Set[str]],
    ):
        self.productions = productions
        self.start_symbol = start_symbol
        self.terminals = terminals
        self.non_terminals = non_terminals
        self.actions = actions
        self.firsts = firsts
        self.follows = follows

    def get_productions(self, lhs: str):
        for production in self.productions:
            if production.lhs == lhs:
                return production

    def get_non_terminals(self):
        return self.non_terminals

    def get_terminals(self):
        return self.terminals
    
    def get_actions(self):
        return self.actions

    def is_non_terminal(self, symbol):
        return symbol in self.get_non_terminals()

    def is_terminal(self, symbol):
        return symbol in self.get_terminals()
    
    def is_action(self, symbol):
        return symbol in self.get_actions()

    def is_epsilon(self, symbol):
        return symbol == EPSILON

    def is_start_symbol(self, symbol):
        return symbol == self.start_symbol

    def get_first(self, symbol):
        if self.is_terminal(symbol):
            return {symbol}
        return self.firsts[symbol]

    def get_follow(self, symbol):
        return self.follows[symbol]
    
    def filter_actions(self, rhs):
        return [symbol for symbol in rhs if not self.is_action(symbol)]

    def entry_tokens_for_rhs(self, lhs: str, rhs: List[str]):
        entry_tokens = set([EPSILON])
        for symbol in self.filter_actions(rhs):
            entry_tokens.remove(EPSILON)
            first = self.get_first(symbol)
            entry_tokens.update(first)
            if EPSILON not in first:
                break
        if EPSILON in entry_tokens:
            entry_tokens.remove(EPSILON)
            entry_tokens.update(self.get_follow(lhs))
        return entry_tokens


class ParseTreeNode(object):
    def __init__(self, symbol: str):
        self.symbol = symbol

    @abstractmethod
    def to_anytree(self, parent=None):
        pass


class ParseTreeEpsilonNode(ParseTreeNode):
    def __init__(self, symbol: str):
        super().__init__(symbol)

    def to_anytree(self, parent=None):
        root = Node(self.symbol, parent=parent)
        Node(EPSILON.lower(), parent=root)
        return root


class ParseTreeLeafNode(ParseTreeNode):
    def __init__(self, symbol: str, token: Token):
        super().__init__(symbol)
        self.token = token

    def to_anytree(self, parent=None):
        if self.token.type == TokenType.EOF:
            return Node(self.token.value, parent=parent)
        return Node(f"({self.token.type.value}, {self.token.value})", parent=parent)


class ParseTreeInternalNode(ParseTreeNode):
    def __init__(self, symbol: str, children: List[ParseTreeNode]):
        super().__init__(symbol)
        self.children = children

    def to_anytree(self, parent=None):
        node = Node(f"{self.symbol}", parent=parent)
        for child in self.children:
            if not isinstance(child, ParseTreeSyntaxErrorNode):
                child.to_anytree(parent=node)
        return node


class SyntaxErrorType(Enum):
    IllegalSymbol = 1
    MissingSymbol = 2
    UnexpectedEOF = 3


class ParseTreeSyntaxErrorNode(ParseTreeNode):
    def __init__(self, symbol: str, line_number: int, error_type: SyntaxErrorType):
        super().__init__(symbol)
        self.line_number = line_number
        self.error_type = error_type

    def __str__(self) -> str:
        if self.error_type == SyntaxErrorType.IllegalSymbol:
            return f"#{self.line_number} : syntax error, illegal {self.symbol}"
        if self.error_type == SyntaxErrorType.MissingSymbol:
            return f"#{self.line_number} : syntax error, missing {self.symbol}"
        if self.error_type == SyntaxErrorType.UnexpectedEOF:
            return f"#{self.line_number} : syntax error, Unexpected EOF"


class ParseTree(object):
    def __init__(self, root: ParseTreeNode):
        self.root = root

    def to_anytree(self):
        return self.root.to_anytree()

    def get_errors(self):
        return self.root.get_errors()


def compile_productions():
    productions = []
    for line in open("grammar/grammar.txt"):
        line = line.strip()
        lhs, rhs_raw = line.split(" ⟶ ")
        rhs = [r.split(" ") for r in rhs_raw.split(" | ")]
        productions.append(Production(lhs, rhs))
    for rhs in productions[0].rhs:
        rhs.append("$")
    return productions, productions[0].lhs


def get_terminals_and_non_terminals_and_actions(productions):
    non_terminals = {production.lhs for production in productions}
    terminals = set()
    actions = set()
    for production in productions:
        for rhs in production.rhs:
            for symbol in rhs:
                if symbol not in non_terminals:
                    if symbol.startswith("#"):
                        actions.add(symbol)
                    else:
                        terminals.add(symbol)
    terminals.add("$")
    return terminals, non_terminals, actions


def get_firsts():
    with open("grammar/first.txt") as f:
        header = f.readline().strip().split()[1:]
        firsts = {}
        for line in f:
            line = line.strip().split()
            symbol = line[0]
            answers = line[1:]
            firsts[symbol] = set(
                header[i] for i, answer in enumerate(answers) if answer == "+"
            )
    return firsts


def get_follows():
    with open("grammar/follow.txt") as f:
        header = f.readline().strip().split()[1:]
        follows = {}
        for line in f:
            line = line.strip().split()
            symbol = line[0]
            answers = line[1:]
            follows[symbol] = set(
                header[i] for i, answer in enumerate(answers) if answer == "+"
            )
    return follows


def get_grammar():
    productions, start_symbol = compile_productions()
    terminals, non_terminals, actions = get_terminals_and_non_terminals_and_actions(productions)
    firsts = get_firsts()
    follows = get_follows()
    return Grammar(productions, start_symbol, terminals, non_terminals, actions, firsts, follows)


class Parser(object):
    def __init__(self, lexer):
        self.grammar = get_grammar()
        self.lexer = lexer
        self.errors = []
        self.code_generator = CodeGenerator(self, lexer)

    def parse(self):
        self.lexer.get_next_token()
        root, eof = self.parse_node(self.grammar.start_symbol, 0)
        return ParseTree(root), self.errors

    def parse_node(self, parsing_symbol, depth):
        token = self.lexer.get_current_token()
        if self.grammar.is_terminal(parsing_symbol):
            if (
                (
                    token.type in [TokenType.KEYWORD, TokenType.SYMBOL, TokenType.EOF]
                    and token.value == parsing_symbol
                )
                or (token.type == TokenType.NUM and parsing_symbol == "NUM")
                or (token.type == TokenType.ID and parsing_symbol == "ID")
            ):
                self.lexer.get_next_token()
                return ParseTreeLeafNode(parsing_symbol, token), False
            else:
                error = ParseTreeSyntaxErrorNode(
                    parsing_symbol, self.lexer.lineno, SyntaxErrorType.MissingSymbol
                )
                self.errors.append(error)
                return error, False
        else:
            production = self.grammar.get_productions(parsing_symbol)
            for rhs in production.rhs:
                entry_tokens = self.grammar.entry_tokens_for_rhs(parsing_symbol, rhs)
                if (
                    (
                        token.type
                        in [TokenType.KEYWORD, TokenType.SYMBOL, TokenType.EOF]
                        and token.value in entry_tokens
                    )
                    or (token.type == TokenType.NUM and "NUM" in entry_tokens)
                    or (token.type == TokenType.ID and "ID" in entry_tokens)
                ):
                    if len(rhs) == 1 and rhs[0] == EPSILON:
                        return ParseTreeEpsilonNode(parsing_symbol), False
                    children = []
                    for symbol in rhs:
                        if self.grammar.is_action(symbol):
                            self.code_generator.code_gen(symbol)
                        else:
                            sub_root, eof = self.parse_node(symbol, depth + 1)
                            children.append(sub_root)
                            if eof:
                                break
                    return ParseTreeInternalNode(parsing_symbol, children), eof
            if token.value in self.grammar.get_follow(parsing_symbol):
                error = ParseTreeSyntaxErrorNode(
                    parsing_symbol, self.lexer.lineno, SyntaxErrorType.MissingSymbol
                )
                self.errors.append(error)
                return error, False
            else:
                if token.type == TokenType.EOF:
                    error = ParseTreeSyntaxErrorNode(
                        token.value, self.lexer.lineno, SyntaxErrorType.UnexpectedEOF
                    )
                    self.errors.append(error)
                    return error, True
                self.errors.append(
                    ParseTreeSyntaxErrorNode(
                        token.type.value
                        if token.type in [TokenType.NUM, TokenType.ID]
                        else token.value,
                        self.lexer.lineno,
                        SyntaxErrorType.IllegalSymbol,
                    )
                )
                self.lexer.get_next_token()
                sub_root, eof = self.parse_node(parsing_symbol, depth)
                return sub_root, eof
