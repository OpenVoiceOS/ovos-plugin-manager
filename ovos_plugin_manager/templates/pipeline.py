from collections import namedtuple
from typing import Optional, Dict

# Intent match response tuple, ovos-core expects PipelinePlugin to return this data structure
# intent_service: Name of the service that matched the intent
# intent_type: intent name (used to call intent handler over the message bus)
# intent_data: data provided by the intent match
# skill_id: the skill this handler belongs to
IntentMatch = namedtuple('IntentMatch',
                         ['intent_service', 'intent_type',
                          'intent_data', 'skill_id', 'utterance']
                         )


class PipelinePlugin:
    """This class is a placeholder, this API will be defined in ovos-core release 0.1.0"""
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
