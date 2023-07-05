class CodeGenerator:
    def __init__(self, parser, lexer) -> None:
        self.parser = parser
        self.lexer = lexer

    def code_gen(self, action) -> None:
        if action == "#add":
            self.action_add()
        elif action == "#sub":
            self.action_sub()
        elif action == "#mul":
            self.action_mul()

    def action_add(self) -> None:
        pass

    def action_sub(self) -> None:
        pass

    def action_mul(self) -> None:
        pass
