class ProxymowException(Exception):
    '''A base class for Proxymow exceptions'''
    pass


class SharedMemoryException(ProxymowException):
    '''Shared Memory for Virtual Mower Unavailable'''
    pass


class RecordNotFoundException(ProxymowException):
    '''Record referenced by id not found'''
    pass


class AttributeNotFoundException(ProxymowException):
    '''Attribute referenced by name not found'''
    pass


class DuplicateRecordException(ProxymowException):
    '''Duplicate Record attempt'''
    pass


class MissingClassException(ProxymowException):
    '''xml Collection missing class attribute'''
    pass


class CollectionNotExtensibleException(ProxymowException):
    '''xml Collection not extensible'''
    pass


class CollectionNotDeletableException(ProxymowException):
    '''xml Collection not deleteable'''
    pass


class CollectionNotUpdatableException(ProxymowException):
    '''xml Collection not updatable'''
    pass
