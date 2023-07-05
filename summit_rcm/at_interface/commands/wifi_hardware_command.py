"""
File that consists of the WiFiHardware Command Functionality
"""
from typing import List, Tuple
from syslog import LOG_ERR, syslog
from summit_rcm.at_interface.commands.command import Command
from summit_rcm.services.network_service import NetworkService


class WiFiHardwareCommand(Command):
    """
    AT Command to get the Wi-Fi Hardware Status
    """

    NAME: str = "Get Wi-Fi Hardware Status"
    SIGNATURE: str = "at+whard"
    VALID_NUM_PARAMS: List[int] = [1]
    DEVICE_TYPE: str = ""

    @staticmethod
    async def execute(params: str) -> Tuple[bool, str]:
        (valid, params_dict) = WiFiHardwareCommand.parse_params(params)
        if not valid:
            return (
                True,
                f"\r\nInvalid Parameters: See Usage - {WiFiHardwareCommand.SIGNATURE}?\r\n",
            )
        try:
            wifi_enabled = await NetworkService().get_wireless_hardware_enabled()
            return (True, f"\r\n+WHARD: {1 if wifi_enabled else 0}\r\nOK\r\n")
        except Exception as exception:
            syslog(
                LOG_ERR, f"Error getting Wi-Fi hardware enabled status: {str(exception)}"
            )
            return (True, "\r\nERROR\r\n")

    @staticmethod
    def parse_params(params: str) -> Tuple[bool, dict]:
        valid = True
        params_dict = {}
        params_list = params.split(",")
        valid &= len(params_list) in WiFiHardwareCommand.VALID_NUM_PARAMS
        for param in params_list:
            valid &= param == ""
        return (valid, params_dict)

    @staticmethod
    def usage() -> str:
        return "\r\nAT+WHARD\r\n"

    @staticmethod
    def signature() -> str:
        return WiFiHardwareCommand.SIGNATURE

    @staticmethod
    def name() -> str:
        return WiFiHardwareCommand.NAME