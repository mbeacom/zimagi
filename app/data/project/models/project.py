from django.conf import settings

from systems import models
from data.environment import models as env

import json


class ProjectFacade(models.ProviderModelFacade):

    def get_packages(self):
        return super().get_packages() + ['project']


    def ensure(self, env, user):
        project = self.retrieve(settings.CORE_PROJECT)

        if not project:
            self.store(settings.CORE_PROJECT, 
                type = 'internal'
            )


    def key(self):
        return 'name'
 
    def scope(self, fields = False):
        if fields:
            return ('environment',)
        
        curr_env = env.Environment.facade.get_env()
        if not curr_env:
            return False

        return { 'environment_id': curr_env }


class Project(models.AppProviderModel):
    name = models.CharField(max_length=128)
    type = models.CharField(null=True, max_length=128)   
    remote = models.CharField(null=True, max_length=256)
    reference = models.CharField(null=True, max_length=128)
 
    environment = models.ForeignKey(env.Environment, related_name='projects', on_delete=models.PROTECT)

    class Meta:
        unique_together = ('environment', 'name')
        facade_class = ProjectFacade

    def __str__(self):
        return "{} ({})".format(self.name, self.type)


    def initialize(self, command):
        self.provider = command.get_provider('project', self.type, instance = self)
        return True
