from functools import lru_cache

from django.conf import settings

from settings import core as app_settings
from systems.models.index import Model, ModelFacade
from utility import data


class ConfigFacade(ModelFacade('config')):

    def ensure(self, command, reinit):
        terminal_width = command.display_width

        if not reinit:
            command.notice(
                "\n".join([
                    "Loading Zimagi system configurations",
                    "-" * terminal_width
                ])
            )

        self.clear(groups__name = 'system')
        command.config_provider.store('environment', {
                'value': command._environment.get_env(),
                'value_type': 'str'
            },
            groups = ['system']
        )
        for setting in self.get_settings():
            command.config_provider.store(setting['name'], {
                    'value': setting['value'],
                    'value_type': setting['type']
                },
                groups = ['system']
            )
        if not reinit:
            command.notice("-" * terminal_width)

    def keep(self):
        keep = ['environment']
        for setting in self.get_settings():
            keep.append(setting['name'])
        return keep


    @lru_cache(maxsize = None)
    def get_settings(self):
        settings_variables = []
        for setting in dir(app_settings):
            if setting == setting.upper():
                value = getattr(app_settings, setting)
                value_type = type(value).__name__

                if value_type in ('bool', 'int', 'float', 'str', 'list', 'dict'):
                    settings_variables.append({
                        'name': "{}_{}".format(settings.APP_SERVICE.upper(), setting),
                        'value': value,
                        'type': value_type
                    })
        return settings_variables


class Config(Model('config')):

    def save(self, *args, **kwargs):
        self.value = data.format_value(self.value_type, self.value)
        super().save(*args, **kwargs)
