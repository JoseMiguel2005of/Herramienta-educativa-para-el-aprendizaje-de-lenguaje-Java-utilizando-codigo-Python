"""Blueprints modulares con nombres de endpoint planos (compatibles con todas las plantillas)."""

from flask import Blueprint
from flask.sansio.blueprints import BlueprintSetupState
from flask.sansio.scaffold import _endpoint_from_view_func


class _FlatBlueprintSetupState(BlueprintSetupState):
    """Registra las reglas del blueprint sin prefijo de nombre para conservar endpoints existentes."""

    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        if self.url_prefix is not None:
            if rule:
                rule = "/".join((self.url_prefix.rstrip("/"), rule.lstrip("/")))
            else:
                rule = self.url_prefix
        options.setdefault("subdomain", self.subdomain)
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)
        defaults = self.url_defaults
        if "defaults" in options:
            defaults = dict(defaults, **options.pop("defaults"))

        self.app.add_url_rule(
            rule,
            endpoint,
            view_func,
            defaults=defaults,
            **options,
        )


class FlatBlueprint(Blueprint):
    """Blueprint de Flask que mantiene nombres de endpoint exactos sin prefijo 'bp.'."""

    def make_setup_state(self, app, options, first_registration=False):
        return _FlatBlueprintSetupState(self, app, options, first_registration)


def register_blueprints(app):
    """Registra todos los blueprints de la aplicación."""
    from py2java.blueprints.api import bp as api_bp
    from py2java.blueprints.auth import bp as auth_bp
    from py2java.blueprints.evaluations import bp as evaluations_bp
    from py2java.blueprints.lessons import bp as lessons_bp
    from py2java.blueprints.practice import bp as practice_bp
    from py2java.blueprints.superadmin import bp as superadmin_bp
    from py2java.blueprints.teacher import bp as teacher_bp

    for blueprint in (
        auth_bp,
        lessons_bp,
        practice_bp,
        evaluations_bp,
        teacher_bp,
        superadmin_bp,
        api_bp,
    ):
        app.register_blueprint(blueprint)
