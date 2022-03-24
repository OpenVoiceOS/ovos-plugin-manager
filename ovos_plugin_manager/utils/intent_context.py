import time

from ovos_utils.log import LOG


class ContextManagerFrame:
    """
    Manages entities and context for a single frame of conversation.
    Provides simple equality querying.
    Attributes:
        entities(list): Entities that belong to ContextManagerFrame
        metadata(object): metadata to describe context belonging to ContextManagerFrame
    """

    def __init__(self, entities=None, metadata=None):
        """
        Initialize ContextManagerFrame
        Args:
            entities(list): List of Entities...
            metadata(object): metadata to describe context?
        """
        self.entities = entities or []
        self.metadata = metadata or {}

    def metadata_matches(self, query=None):
        """
        Returns key matches to metadata
        Asserts that the contents of query exist within (logical subset of)
        metadata in this frame.
        Args:
            query(object): metadata for matching
        Returns:
            bool:
                True: when key count in query is > 0 and all keys in query in
                    self.metadata
                False: if key count in query is <= 0 or any key in query not
                    found in self.metadata
        """
        query = query or {}
        result = len(query.keys()) > 0
        for key in query.keys():
            result = result and query[key] == self.metadata.get(key)

        return result

    def merge_context(self, tag, metadata):
        """
        merge into contextManagerFrame new entity and metadata.
        Appends tag as new entity and adds keys in metadata to keys in
        self.metadata.
        Args:
            tag(str): entity to be added to self.entities
            metadata(object): metadata containes keys to be added to self.metadata
        """
        self.entities.append(tag)
        for k, v in metadata.items():
            if k not in self.metadata:
                self.metadata[k] = v


class ContextManager:
    """
    ContextManager
    Use to track context throughout the course of a conversational session.
    How to manage a session's lifecycle is not captured here.
    """

    def __init__(self, timeout):
        self.frame_stack = []
        self.timeout = timeout * 60  # minutes to seconds

    def clear_context(self):
        self.frame_stack = []

    def remove_context(self, context_id):
        for context, ts in list(self.frame_stack):
            ents = context.entities[0].get('data', [])
            for e in ents:
                if context_id == e:
                    self.frame_stack.remove((context, ts))

    def inject_context(self, entity, metadata=None):
        """
        Args:
            entity(object): Format example...
                               {'data': 'Entity tag as <str>',
                                'key': 'entity proper name as <str>',
                                'confidence': <float>'
                               }
            metadata(object): dict, arbitrary metadata about entity injected
        """
        metadata = metadata or {}
        try:
            if len(self.frame_stack) > 0:
                top_frame = self.frame_stack[0]
            else:
                top_frame = None
            if top_frame and top_frame[0].metadata_matches(metadata):
                top_frame[0].merge_context(entity, metadata)
            else:
                frame = ContextManagerFrame(entities=[entity],
                                            metadata=metadata.copy())
                self.frame_stack.insert(0, (frame, time.time()))
        except (IndexError, KeyError):
            pass
        except Exception as e:
            LOG.exception(e)

    def get_context(self, max_frames=5, missing_entities=None):
        """ Constructs a list of entities from the context.

        Args:
            max_frames(int): maximum number of frames to look back
            missing_entities(list of str): a list or set of tag names,
            as strings

        Returns:
            list: a list of entities

        """
        try:
            missing_entities = missing_entities or []

            relevant_frames = [frame[0] for frame in self.frame_stack if
                               time.time() - frame[1] < self.timeout]

            if not max_frames or max_frames > len(relevant_frames):
                max_frames = len(relevant_frames)

            missing_entities = list(missing_entities)

            context = []
            last = ''
            depth = 0
            for i in range(max_frames):
                frame_entities = [entity.copy() for entity in
                                  relevant_frames[i].entities]
                for entity in frame_entities:
                    entity['confidence'] = entity.get('confidence', 1.0) \
                                           / (2.0 + depth)
                context += frame_entities

                # Update depth
                if entity['origin'] != last or entity['origin'] == '':
                    depth += 1
                last = entity['origin']
            result = []
            if len(missing_entities) > 0:

                for entity in context:
                    if entity.get('data') in missing_entities:
                        result.append(entity)
                        # NOTE: this implies that we will only ever get one
                        # of an entity kind from context, unless specified
                        # multiple times in missing_entities. Cannot get
                        # an arbitrary number of an entity kind.
                        missing_entities.remove(entity.get('data'))
            else:
                result = context

            # Only use the latest instance of each keyword
            stripped = []
            processed = []
            for f in result:
                keyword = f['data'][0][1]
                if keyword not in processed:
                    stripped.append(f)
                    processed.append(keyword)
            result = stripped
        except Exception as e:
            LOG.exception(e)
            return []
        # LOG.debug("Adapt Context: {}".format(result))
        return result
