"""
Module to support configuration of the radio's SISO mode parameter.
"""

import os
from subprocess import run
from syslog import LOG_ERR, syslog


class RadioSISOModeService:
    """
    Exposes functionality to get/set the SISO mode (MIMO, ANT0, ANT1) used by the lrdmwl driver
    module.
    """

    LRDMWL_MODULE_PATH = "/sys/module/lrdmwl"
    LRDMWL_HOLDERS_PATH = f"{LRDMWL_MODULE_PATH}/holders"
    SISO_MODE_PARAMETER_PATH = f"{LRDMWL_MODULE_PATH}/parameters/SISO_mode"
    MODPROBE_PATH = "/usr/sbin/modprobe"
    SISO_MODE_SYSTEM_DEFAULT = -1
    SISO_MODE_MIMO = 0
    SISO_MODE_ANT0 = 1
    SISO_MODE_ANT1 = 2
    SISO_MODES = [
        SISO_MODE_SYSTEM_DEFAULT,
        SISO_MODE_MIMO,
        SISO_MODE_ANT0,
        SISO_MODE_ANT1,
    ]

    @staticmethod
    def get_running_driver_interface() -> str:
        """
        Retrieves the current specific interface lrdmwl driver currently in use by the system (e.g.,
        lrdmwl_sdio, lrdmwl_pcie)
        """
        try:
            return os.listdir(RadioSISOModeService.LRDMWL_HOLDERS_PATH)[0]
        except Exception as exception:
            syslog(
                LOG_ERR, f"Unable to read current driver interface - {str(exception)}"
            )
            return ""

    @staticmethod
    def get_current_siso_mode() -> int:
        """
        Retrieve the current SISO_mode parameter from the driver
        """
        with open(
            RadioSISOModeService.SISO_MODE_PARAMETER_PATH, "r"
        ) as siso_mode_parameter:
            siso_mode = int(siso_mode_parameter.readline().strip())
            if siso_mode not in RadioSISOModeService.SISO_MODES:
                raise Exception("invalid parameter value")

            return siso_mode

    @staticmethod
    def set_siso_mode(siso_mode: int) -> None:
        """
        Unload and then reload the lrdmwl and lrdmwl_sdio driver modules to use the desired SISO
        mode.
        """
        if siso_mode not in RadioSISOModeService.SISO_MODES:
            raise Exception("invalid parameter value")

        if siso_mode == RadioSISOModeService.get_current_siso_mode():
            # Already using the desired SISO mode
            return

        driver_interface = RadioSISOModeService.get_running_driver_interface()
        if driver_interface == "":
            raise Exception("unable to determine current driver interface")

        # Unload the driver
        proc = run(
            [RadioSISOModeService.MODPROBE_PATH, "-r", driver_interface, "lrdmwl"],
        )
        if proc.returncode:
            raise Exception("unable to unload lrdmwl driver")

        # Reload the driver with the new SISO_mode parameter unless the system default is requested
        # ('siso_mode' == -1). In that case, just load the 'lrdmwl' driver module without any
        # parameters.
        proc = run(
            [
                RadioSISOModeService.MODPROBE_PATH,
                "lrdmwl",
                f"SISO_mode={str(siso_mode)}"
                if siso_mode is not RadioSISOModeService.SISO_MODE_SYSTEM_DEFAULT
                else "",
            ],
        )
        if proc.returncode:
            raise Exception("unable to reload lrdmwl driver module")
        proc = run(
            [RadioSISOModeService.MODPROBE_PATH, driver_interface],
        )
        if proc.returncode:
            raise Exception(f"unable to reload {driver_interface} driver module")
