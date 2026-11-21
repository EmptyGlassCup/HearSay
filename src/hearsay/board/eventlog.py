from hearsay.protocol.events import Event

class EventLog:
    def __init__(self):
        self.event_log = []
    
    def append(self, event: Event):
        assert event.sequence is None, "Event already has a set sequence number."
        sequence_no = len(self.event_log)
        event.sequence = sequence_no
        self.event_log.append(event)
    
    def __iter__(self):
        return iter(self.event_log)