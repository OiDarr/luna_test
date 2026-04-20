from faststream import FastStream

from app.messaging import broker
from consumer import worker  # noqa: F401

app = FastStream(broker)
