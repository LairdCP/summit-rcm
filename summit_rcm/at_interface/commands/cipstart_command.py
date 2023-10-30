from typing import List, Tuple
from summit_rcm.at_interface.commands.command import Command
from summit_rcm.at_interface.connection_service import ConnectionService


class CIPSTARTCommand(Command):
    NAME: str = "Start IP connection"
    SIGNATURE: str = "at+cipstart"
    VALID_NUM_PARAMS: List[int] = [4, 5]

    @staticmethod
    async def execute(params: str) -> Tuple[bool, str]:
        (valid, params_dict) = CIPSTARTCommand.parse_params(params)
        if not valid:
            return (
                True,
                f"\r\nInvalid Parameters: See Usage - {CIPSTARTCommand.SIGNATURE}?\r\n",
            )
        if not ConnectionService.validate_connection_type(params_dict["type"]):
            return (True, "\r\nCONNECTION TYPE ERROR\r\n")

        if ConnectionService().start_connection(
            id=params_dict["connection_id"],
            type=params_dict["type"],
            addr=params_dict["remote_ip"],
            port=params_dict["remote_port"],
            keepalive=params_dict["keepalive"],
        ):
            return (True, "\r\nOK\r\n")
        else:
            return (True, "\r\nCONNECTION START ERROR\r\n")

    @staticmethod
    def parse_params(params: str) -> Tuple[bool, dict]:
        valid = True
        params_dict = {}
        params_list = params.split(",")
        given_num_param = len(params_list)
        valid &= given_num_param in CIPSTARTCommand.VALID_NUM_PARAMS
        for param in params_list:
            valid &= param != ""
        if valid:
            try:
                params_dict["connection_id"] = int(params_list[0])
                params_dict["type"] = params_list[1].lower()
                params_dict["remote_ip"] = params_list[2]
                params_dict["remote_port"] = params_list[3]
                params_dict["keepalive"] = (
                    int(params_list[4]) if given_num_param == 5 else 0
                )
            except Exception:
                valid = False
        return (valid, params_dict)

    @staticmethod
    def usage() -> str:
        return (
            "\r\nAT+CIPSTART=<connection id>,<type>,<remote IP>,"
            "<remote port>[,<keepalive>]\r\n"
        )

    @staticmethod
    def signature() -> str:
        return CIPSTARTCommand.SIGNATURE

    @staticmethod
    def name() -> str:
        return CIPSTARTCommand.NAME