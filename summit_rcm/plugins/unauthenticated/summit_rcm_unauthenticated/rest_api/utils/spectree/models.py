"""Module to hold SpecTree Models"""

from pydantic import BaseModel
from summit_rcm.rest_api.utils.spectree.models import DefaultResponseModelLegacy


class AllowUnauthenticatedRebootResetStateModel(BaseModel):
    """Model for the response to a request for the allowUnauthenticatedRebootReset state"""

    allowUnauthenticatedRebootReset: bool


class AllowUnauthenticatedRebootResetStateModelLegacy(DefaultResponseModelLegacy):
    """Model for the response to a request for the allowUnauthenticatedRebootReset state (legacy)"""

    allowUnauthenticatedRebootReset: bool
