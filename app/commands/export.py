from systems.commands.index import Command


class Export(Command('export')):

    def exec(self):
        self.options.add('module_name', 'core')
        self.module.provider.export_profile(
            self.profile_components
        )
