class CodeGenerator:
    def __init__(self, parser, lexer) -> None:
        self.parser = parser
        self.lexer = lexer
        self.semantic_stack = list()
        self.jump_address = dict()
        self.codes_generated = list()

    def code_gen(self, action) -> None:
        pass