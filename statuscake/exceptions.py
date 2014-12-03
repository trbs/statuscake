
class StatusCakeError(Exception):
    pass


class StatusCakeAuthError(StatusCakeError):
    pass


class StatusCakeNotLinkedError(StatusCakeError):
    pass


class StatusCakeFieldMissingError(StatusCakeError):
    pass


class StatusCakeFieldError(StatusCakeError):
    pass


class StatusCakeResponseError(StatusCakeError):
    pass
