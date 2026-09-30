"""Authenticated work-hub endpoints sharing the existing engine's authority and scope."""
from .core import PolicyError


class WorkHub:
    def __init__(self, service):
        self.service = service
        self.store = service.store

    def _project(self, data, write=False):
        project = data.get('project_id') or data.get('project')
        if not isinstance(project, str) or not project or project == '*':
            raise PolicyError('Choose one project first.')
        return self.service._scope({'project': project}, write=write)

    def get(self, path, data):
        project = self._project(data)
        if path == '/api/work-hub/imports':
            from .work_import import WorkImports
            return {'entries': WorkImports(self.store).entries(project)}
        if path == '/api/work-hub/search':
            from .search import Search
            return Search(self.store).run(data.get('query', ''), project_id=project)
        if path == '/api/work-hub/procedures':
            from .recipes import RecipeLibrary
            return RecipeLibrary(self.store).procedure(project, data.get('recipe_id'), data.get('version'))
        if path == '/api/work-hub/outcomes':
            from .task_outcomes import TaskOutcomes
            outcomes = TaskOutcomes(self.store)
            return outcomes.view(data['job_id'], project) if data.get('job_id') else outcomes.summary(project)
        raise PolicyError('Unknown work hub view.')

    def act(self, path, data):
        if not isinstance(data, dict):
            raise PolicyError('Provide a work hub request.')
        project = self._project(data, write=True)
        if path == '/api/work-hub/origin':
            from .input_origins import InputOrigins
            return InputOrigins(self.store).queue(data.get('donor_id'), project,
                                                  data.get('transcript_id'), data.get('text'))
        if path == '/api/work-hub/imports':
            from .work_import import WorkImports
            imports = WorkImports(self.store)
            action = data.get('action')
            if action == 'preview':
                return imports.preview(project, data.get('content'), format=data.get('format', 'text'),
                                       source=data.get('source', 'other'), source_id=data.get('source_id', ''),
                                       title=data.get('title', ''))
            if action == 'confirm':
                return imports.confirm(data.get('preview_id'), data.get('digest'), project,
                                       confirm=data.get('confirm') is True)
            raise PolicyError('Choose preview or confirm.')
        if path == '/api/work-hub/procedures':
            from .recipes import RecipeLibrary
            recipes = RecipeLibrary(self.store)
            action = data.get('action')
            common = (project, data.get('recipe_id'), data.get('version'))
            if action == 'review':
                return recipes.review_procedure(*common, job_id=data.get('job_id'),
                                                 note=data.get('note', ''), confirm=data.get('confirm') is True)
            if action == 'retire':
                return recipes.retire_procedure(*common, confirm=data.get('confirm') is True)
            if action == 'restore':
                return recipes.restore_procedure(*common, confirm=data.get('confirm') is True)
            raise PolicyError('Choose review, retire or restore.')
        if path == '/api/work-hub/outcomes':
            from .task_outcomes import TaskOutcomes
            return TaskOutcomes(self.store).feedback(data.get('job_id'), project, data.get('response'))
        raise PolicyError('Unknown work hub action.')
