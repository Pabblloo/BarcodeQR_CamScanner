from typing import Type, Optional, Union, Callable
from inspect import signature


class EventProcessor:
    def __init__(self, ):
        self.handlers = []

    def add_handler(self, handler: Callable[[Type[Event]], None]):
        event_type = self._get_handler_eventtype(handler)
        if not issubclass(event_type, Event):
            message = ("Event isn't instance of base ``Event`` class")
            raise ValueError(message)
        self.handlers.append(handler)

    def process_event(self, event: Type[Event]) -> None:
        event_types = map(self._get_handler_eventtype, self.handlers)
        for event_type, handler in zip(event_types, self.handlers):
            # TODO: possible type inheritation
            # if type(event) is event_type:
            if issubclass(type(event), event_type):
                handler(event)

    def _get_handler_eventtype(
            self,
            handler: Callable[[Type[Event]], None],
    ) -> type:
        sig = signature(handler)
        if len(sig.parameters) != 1:
            message = ("Event ``handler`` must contains exactly 1 argument: "
                       "event for processing")
            raise ValueError(message)

        # TODO: check type of event

        param, *_ = sig.parameters.values()
        event_type = param.annotation
        return event_type
