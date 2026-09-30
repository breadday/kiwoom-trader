"""JSON parsing safeguards shared by durable local state loaders."""

import json


def load_state_json(text):
    """Reject duplicate keys at every object level instead of overwriting them."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("state JSON contains duplicate keys")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=unique_object)
