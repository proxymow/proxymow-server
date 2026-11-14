class ProxymowException(Exception):
    '''A base class for Proxymow exceptions'''


class SharedMemoryException(ProxymowException):
    '''Shared Memory for Virtual Mower Unavailable'''


class RecordNotFoundException(ProxymowException):
    '''Record referenced by id not found'''


class AttributeNotFoundException(ProxymowException):
    '''Attribute referenced by name not found'''


class DuplicateRecordException(ProxymowException):
    '''Duplicate Record attempt'''


class MissingClassException(ProxymowException):
    '''xml Collection missing class attribute'''


class CollectionNotExtensibleException(ProxymowException):
    '''xml Collection not extensible'''


class CollectionNotDeletableException(ProxymowException):
    '''xml Collection not deleteable'''


class CollectionNotUpdatableException(ProxymowException):
    '''xml Collection not updatable'''
