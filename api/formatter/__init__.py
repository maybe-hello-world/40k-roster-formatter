import os

import azure.functions
import logging
import io
import json

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from .rosterview import RosterView
from .utils import FormatterException
from .formats import RussianTournamentsPrinter, WTCPrinter, DefaultPrinter

sentry_logging = LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.WARNING  # Send errors as events
)

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[sentry_logging],
    debug=True,
    attach_stacktrace=True,

    traces_sample_rate=1.0
)

logging.basicConfig()


def main(req: azure.functions.HttpRequest) -> azure.functions.HttpResponse:
    logging.debug("HTTP trigger fired")
    try:
        options = req.form.to_dict()
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
            logging.error(f"Provided incorrect filename", extra={"40k_filename": filename})
            raise FormatterException(
                "Provided file doesn't end with .ros or .rosz and therefore "
                "couldn't be parsed as valid BattleScribe file."
            )
        logging.debug("Roster successfully parsed.")

        print_format = options.get('formats', 'default')

        if print_format == 'rus':
            representation = RussianTournamentsPrinter().print(result)
        elif print_format == 'wtc':
            representation = WTCPrinter().print(result)
        else:
            representation = DefaultPrinter().print(result)

        answer = {
            'info': representation,
            'debug': result.debug_info
        }

        return azure.functions.HttpResponse(json.dumps(answer), status_code=200, mimetype='application/json')

    except Exception as e:
        logging.exception(e)
        return azure.functions.HttpResponse(json.dumps({'info': str(e), 'debug': ''}), status_code=400, mimetype='application/json')
