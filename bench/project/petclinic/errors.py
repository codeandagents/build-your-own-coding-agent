"""Errors the clinic code raises."""


class ValidationError(ValueError):
    """Bad input. The message starts with the field's name, then a colon: "name: must not be empty"."""


class NotFound(ValidationError):
    """A record that doesn't exist: "visit_id: no visit 42"."""
