class WorkflowError(RuntimeError):
    """Base error for controlled audit workflow failures."""


class WorkflowBlockedError(WorkflowError):
    """Raised when export or close is blocked by mandatory review items."""


class InvalidWorkflowTransition(WorkflowError):
    """Raised when a UI/controller asks for an invalid transition."""
