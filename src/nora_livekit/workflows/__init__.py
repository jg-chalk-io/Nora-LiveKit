"""Nora workflow components using LiveKit Tasks and Agents.

This module implements the proper LiveKit workflow pattern:
- Tasks for discrete data collection operations
- Agents for conversational control
- Proper handoffs between phases

Key Components:
- CollectUrgentInfoTask: Collects info for urgent transfers
- CollectMessageInfoTask: Collects info for callback messages
- UrgentTransferAgent: Handles urgent transfer flow
- MessageFlowAgent: Handles non-urgent message flow
- CriticalEmergencyAgent: Handles life-threatening emergencies
"""

from .data import (
    UrgentTransferData,
    MessageFlowData,
    CriticalEmergencyData,
)
from .tasks import (
    CollectUrgentInfoTask,
    CollectMessageInfoTask,
    CollectCriticalInfoTask,
)
from .agents import (
    GreeterAgent,
    UrgentTransferAgent,
    MessageFlowAgent,
    CriticalEmergencyAgent,
)

__all__ = [
    # Data classes
    "UrgentTransferData",
    "MessageFlowData",
    "CriticalEmergencyData",
    # Tasks
    "CollectUrgentInfoTask",
    "CollectMessageInfoTask",
    "CollectCriticalInfoTask",
    # Agents
    "GreeterAgent",
    "UrgentTransferAgent",
    "MessageFlowAgent",
    "CriticalEmergencyAgent",
]
