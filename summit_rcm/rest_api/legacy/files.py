"""
Module to handle legacy files endpoint
"""
import os
from syslog import LOG_ERR, syslog
import falcon.asgi.multipart
from summit_rcm.rest_api.services.rest_files_service import (
    RESTFilesService as FilesService,
)
from summit_rcm import definition


class FileManage:
    """File Management"""

    async def on_post(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        result = {"SDCERR": definition.SUMMIT_RCM_ERRORS["SDCERR_FAIL"], "InfoMsg": ""}

        try:
            form = await req.get_media()
        except falcon.MediaNotFoundError as exception:
            result["InfoMsg"] = f"Invalid request - {str(exception.description)}"
            resp.media = result
            return

        if not isinstance(form, falcon.asgi.multipart.MultipartForm):
            result["InfoMsg"] = "Invalid request - multipart form required"
            resp.media = result
            return

        async for part in form:
            if part.name == "type":
                try:
                    type = await part.text
                except Exception:
                    type = None
                break

        if not type:
            syslog("FileManage POST - no type specified")
            result["InfoMsg"] = "file POST - no type specified"
            resp.media = result
            return

        if type not in definition.FILEDIR_DICT:
            syslog(f"FileManage POST type {type} unknown")
            result["InfoMsg"] = f"file POST type {type} unknown"  # bad request
            resp.media = result
            return

        if type == "timezone":
            # We don't support uploading timezone data
            syslog("FileManage POST - timezone data upload not supported")
            result["InfoMsg"] = "file POST - timezone data upload not supported"
            resp.media = result
            return

        if type == "config":
            try:
                # System config import is only available when the encrypted storage toolkit is
                # enabled
                if not FilesService.is_encrypted_storage_toolkit_enabled():
                    syslog(
                        "FileManage POST - "
                        "config import not available on non-encrypted file system images"
                    )
                    resp.status = falcon.HTTP_400
                    return

                password = req.params.get("password", "")
                if not password:
                    resp.status = falcon.HTTP_400
                    return

                async for part in form:
                    if part.name == "file":
                        await FilesService.handle_config_import_file_upload_multipart_form(
                            part
                        )

                        success, msg = await FilesService.import_system_config(password)
                        if not success:
                            raise Exception(msg)

                        result["SDCERR"] = definition.SUMMIT_RCM_ERRORS[
                            "SDCERR_SUCCESS"
                        ]
                        resp.media = result
                        return

                # The form is missing a 'file' part
                syslog("FileManage POST - no filename provided")
                raise Exception("No filename provided")
            except Exception as exception:
                syslog(f"Could not import system configuration - {str(exception)}")
                result[
                    "InfoMsg"
                ] = f"Could not import system configuration - {str(exception)}"
            resp.media = result
            return

        async for part in form:
            if part.name == "file":
                try:
                    fp = await FilesService.handle_cert_file_upload_multipart_form(
                        part, part.secure_filename
                    )
                    if not fp:
                        syslog("FileManage POST type failure to copy file")
                        result[
                            "InfoMsg"
                        ] = "file POST failure to copy file"  # bad request
                        resp.media = result
                        return

                    result["SDCERR"] = definition.SUMMIT_RCM_ERRORS["SDCERR_SUCCESS"]
                    resp.media = result
                    return
                except Exception:
                    syslog("unable to obtain FileManage._lock")
                    result[
                        "InfoMsg"
                    ] = "unable to obtain internal file lock"  # Internal server error
                    resp.media = result
                    return

        # The form is missing a 'file' part
        syslog("FileManage POST - no filename provided")
        result["InfoMsg"] = "file POST - no filename specified"
        resp.media = result

    async def on_get(self, req, resp):
        resp.status = falcon.HTTP_200

        type = req.params.get("type", None)
        if not type:
            syslog("FileManage Get - no filename provided")
            resp.status = falcon.HTTP_400
            return

        archive = ""
        if type == "config":
            password = req.params.get("password", None)
            if not password:
                syslog("FileManage Get - no password provided")
                resp.status = falcon.HTTP_400
                return

            if not FilesService.is_encrypted_storage_toolkit_enabled():
                syslog(
                    "FileManage GET - "
                    "config export not available on non-encrypted file system images"
                )
                resp.status = falcon.HTTP_400
                return

            try:
                success, msg, archive = FilesService.export_system_config(password)
                if not success:
                    raise Exception(msg)

                resp.stream = await FilesService.handle_file_download(archive)
                resp.content_type = falcon.MEDIA_TEXT
                resp.status = 200
                syslog("Configuration zipped for user")
            except Exception as exception:
                syslog(f"Could not export system config - {str(exception)}")
                resp.status = falcon.HTTP_500
            finally:
                if os.path.isfile(archive):
                    os.unlink(archive)
            return
        elif type == "log":
            password = req.params.get("password", None)
            if not password:
                syslog("FileManage Get - no password provided")
                resp.status = falcon.HTTP_400
                return

            try:
                success, msg, archive = FilesService.export_logs(password)
                if not success:
                    raise Exception(msg)

                resp.stream = await FilesService.handle_file_download(archive)
                resp.content_type = falcon.MEDIA_TEXT
                resp.status = 200
                syslog("System log zipped for user")
            except Exception as exception:
                syslog(f"Could not export log data - {str(exception)}")
                resp.status = falcon.HTTP_500
            finally:
                if os.path.isfile(archive):
                    os.unlink(archive)
            return

        elif type == "debug":
            try:
                success, msg, archive = FilesService.export_debug()
                if not success:
                    raise Exception(msg)

                resp.stream = await FilesService.handle_file_download(archive)
                resp.content_type = falcon.MEDIA_TEXT
                resp.status = 200
                syslog("Configuration and system log zipped/encrypted for user")
            except Exception as exception:
                syslog(f"Could not export debug info - {str(exception)}")
                resp.status = falcon.HTTP_500
            finally:
                if os.path.isfile(archive):
                    os.unlink(archive)
            return
        else:
            syslog(f"FileManage GET - unknown file type {type}")
            resp.status = falcon.HTTP_400
        return

    async def on_delete(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        result = {
            "SDCERR": definition.SUMMIT_RCM_ERRORS["SDCERR_FAIL"],
            "InfoMsg": "Unable to delete file",
        }
        type = req.params.get("type", None)
        file = req.params.get("file", None)
        if not type or not file:
            if not type:
                syslog("FileManage DELETE - no type specified")
                result["InfoMsg"] = "no type specified"
            if not file:
                syslog("FileManage DELETE - no filename provided")
                result["InfoMsg"] = "no file specified"
            resp.media = result
            return
        valid = ["cert", "pac"]
        if type not in valid:
            result["InfoMsg"] = f"type not one of {valid}"
            resp.media = result
            return

        try:
            FilesService.delete_cert_file(file)
            result["SDCERR"] = definition.SUMMIT_RCM_ERRORS["SDCERR_SUCCESS"]
            result["InfoMsg"] = f"file {file} deleted"
            syslog(f"file {file} deleted")
        except FileNotFoundError:
            syslog(f"Attempt to remove non-existant file {file}")
            result["InfoMsg"] = f"File: {file} not present"
        except Exception as exception:
            syslog(f"Attempt to remove file {file} did not succeed - {str(exception)}")

        resp.media = result


class FilesManage:
    """Files Management"""

    async def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        result = {
            "SDCERR": definition.SUMMIT_RCM_ERRORS["SDCERR_SUCCESS"],
            "InfoMsg": "",
            "count": 0,
            "files": [],
        }
        type = req.params.get("type", None)
        valid = ["cert", "pac", "network"]
        if not type:
            result["SDCERR"] = definition.SUMMIT_RCM_ERRORS["SDCERR_FAIL"]
            result["InfoMsg"] = "no filename provided"
            resp.content_type = falcon.MEDIA_JSON
            resp.media = result
            return
        if type not in valid:
            result["InfoMsg"] = f"type not one of {valid}"
            result["SDCERR"] = definition.SUMMIT_RCM_ERRORS["SDCERR_FAIL"]
            resp.content_type = falcon.MEDIA_JSON
            resp.media = result
            return

        if type == "network":
            password = req.params.get("password", "")
            if not password or password == "":
                result["InfoMsg"] = "Invalid password"
                resp.content_type = falcon.MEDIA_JSON
                resp.media = result
                return

            try:
                success, msg, archive = FilesService.export_connections(password)
                if not success:
                    raise Exception(msg)

                resp.stream = await FilesService.handle_file_download(archive)
                resp.content_type = falcon.MEDIA_TEXT
            except Exception as exception:
                syslog(LOG_ERR, f"Could not export connections - {str(exception)}")
                resp.status = falcon.HTTP_500
            os.unlink(archive)
            return
        else:
            files = FilesService.get_files_by_type(type)
            result["files"] = files
            result["count"] = len(files)
            result["InfoMsg"] = f"{type} files"
        resp.content_type = falcon.MEDIA_JSON
        resp.media = result

    async def on_put(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        result = {"SDCERR": definition.SUMMIT_RCM_ERRORS["SDCERR_FAIL"], "InfoMsg": ""}

        type = req.params.get("type", None)
        valid_types = ["network"]
        if not type or type not in valid_types:
            result["InfoMsg"] = "Invalid file type"
            resp.media = result
            return

        fp = None
        async for part in await req.get_media():
            if part.name == "archive":
                try:
                    fp = await FilesService.handle_connection_import_file_upload_multipart_form(
                        part
                    )
                except Exception as exception:
                    syslog(f"Could not upload file - {str(exception)}")
                    fp = None
                break

        if not fp:
            result["InfoMsg"] = "Invalid file"
            resp.media = result
            return

        password = req.params.get("password", "")
        if not password or password == "":
            result["InfoMsg"] = "Invalid password"
            resp.media = result
            return

        success, msg = await FilesService.import_connections(password, False)
        if success:
            result["SDCERR"] = definition.SUMMIT_RCM_ERRORS["SDCERR_SUCCESS"]
        else:
            syslog(LOG_ERR, f"Could not import connections - {msg}")
            result["InfoMsg"] = f"Could not import connections - {msg}"

        resp.media = result
