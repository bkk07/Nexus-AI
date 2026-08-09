from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.operations import OperationType


@dataclass
class Operation:
    """
    One operation that the Agent wants to execute.
    """

    operation_type: OperationType

    connector: str

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    depends_on: Optional[int] = None


@dataclass
class ExecutionPlan:
    """
    Complete execution plan for one user request.

    Operations are executed in order unless the executor
    later decides that independent operations can run in parallel.
    """

    operations: list[Operation] = field(
        default_factory=list
    )

    def add_operation(
        self,
        operation_type: OperationType,
        connector: str,
        parameters: Optional[dict[str, Any]] = None,
        depends_on: Optional[int] = None,
    ) -> Operation:

        operation = Operation(
            operation_type=operation_type,
            connector=connector,
            parameters=parameters or {},
            depends_on=depends_on,
        )

        self.operations.append(operation)

        return operation

    def is_empty(self) -> bool:
        return len(self.operations) == 0

    def __len__(self) -> int:
        return len(self.operations)