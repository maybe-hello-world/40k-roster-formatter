import os

import azure.functions
import logging
import json

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


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
    try:
        answer = {'info': 'ok'}
        return azure.functions.HttpResponse(json.dumps(answer), status_code=200, mimetype='application/json')

    except Exception as e:
        logging.exception(e)
        return azure.functions.HttpResponse(json.dumps({
            'info': str(e)
        }), status_code=500, mimetype='application/json')
