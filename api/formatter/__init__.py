import azure.functions
import logging
import io

from .formatter import RosterView, FormatterException


def main(req: azure.functions.HttpRequest) -> azure.functions.HttpResponse:
    logging.debug("HTTP trigger fired")
    try:
        options = req.params
        logging.debug(f"Options: {options}")
        roster = req.files.get('roster', None)  # Werkzeug.datastructures.FileStorage
        if roster is None:
            raise FormatterException("File is not provided.")

        filename: str = roster.filename
        content: bytes = roster.read()
        logging.debug(f"Received file {filename} with length {len(content)} bytes")

        if filename.endswith(".ros"):
            result = RosterView(content.decode('utf-8'), zipped=False, options=options)
        elif filename.endswith(".rosz"):
            result = RosterView(io.BytesIO(content), zipped=True, options=options)
        else:
            raise FormatterException(
                "Provided file doesn't end with .ros or .rosz and therefore "
                "couldn't be parsed as valid BattleScribe file."
            )
        logging.debug("Roster successfully parsed.")
        return azure.functions.HttpResponse(str(result), status_code=200)

    except Exception as e:
        logging.exception(e)
        return azure.functions.HttpResponse(str(e), status_code=400)
