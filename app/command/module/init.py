from systems.command.index import Command


class Init(Command('module.init')):

    def exec(self):
        self._module._ensure(self, True)