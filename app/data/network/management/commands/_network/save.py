from systems.command import types, mixins


class SaveCommand(
    types.NetworkActionCommand
):
    def get_description(self, overview):
        if overview:
            return """add a new network in current environment

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam 
pulvinar nisl ac magna ultricies dignissim. Praesent eu feugiat 
elit. Cras porta magna vel blandit euismod.
"""
        else:
            return """add a new network in current environment
                      
Etiam mattis iaculis felis eu pharetra. Nulla facilisi. 
Duis placerat pulvinar urna et elementum. Mauris enim risus, 
mattis vel risus quis, imperdiet convallis felis. Donec iaculis 
tristique diam eget rutrum.

Etiam sit amet mollis lacus. Nulla pretium, neque id porta feugiat, 
erat sapien sollicitudin tellus, vel fermentum quam purus non sem. 
Mauris venenatis eleifend nulla, ac facilisis nulla efficitur sed. 
Etiam a ipsum odio. Curabitur magna mi, ornare sit amet nulla at, 
scelerisque tristique leo. Curabitur ut faucibus leo, non tincidunt 
velit. Aenean sit amet consequat mauris.
"""
    def parse(self):
        self.parse_test()
        self.parse_force()
        self.parse_network_provider_name('--provider')
        self.parse_network_name()
        self.parse_network_fields(True, self.get_provider('network', 'help').field_help)

    def exec(self):
        if self.check_exists(self._network, self.network_name):
            self.network.provider.update(self.network_fields)
        else:
            self.network_provider.network.create(
                self.network_name, 
                self.network_fields
            )