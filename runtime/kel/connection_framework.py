"""The Connection Framework (V2.0 / V2-04): what every Connection gets, in one place.

A Connection is one kind of thing with three presentations, and this module is where the standard parts
live — the same way for every service, encrypted credential in the OS store by the shell, one outbound
request through `connections.perform_request`, one honest sentence about what happened, and the same
retry policy for everyone.

What the framework is *not*: it is not a per-service mechanism, and it does not know any service by name.
Templates describe the three kinds of credential, and the numbers below are the policy every request
already runs under (`connections.REQUEST_ATTEMPTS` and friends). Actions — what Kel can *do* with a
service — are tools, and they are not built yet: nothing here invents a request Kel is not asked to make.

Design: docs/v2/DECISIONS.md (V2-04).
"""

TEMPLATES = (
    {
        'id': 'api_key',
        'label': 'API key',
        'hint': 'a key Kel sends with its requests',
        'credential_field': 'api_key',
        'credential_label': 'API key',
        'check': 'One authenticated GET at the address you give, and the answer is reported as it is.',
    },
    {
        'id': 'oauth',
        'label': 'Account authorization',
        'hint': 'you sign in and Kel keeps the token',
        'credential_field': 'access_token',
        'credential_label': 'Access token',
        'check': ('One authenticated GET with the token. The sign-in step that produces the token is not '
                  'built yet, so today the token has to be pasted in.'),
    },
    {
        'id': 'bot',
        'label': 'Bot or webhook',
        'hint': 'a bot token or a webhook address',
        'credential_field': 'token',
        'credential_label': 'Bot token',
        'check': 'One authenticated GET at the address you give, with the bot token.',
    },
)


def templates():
    """The three kinds of Connection, as rows — the one place their words live."""
    return [dict(template) for template in TEMPLATES]


def template(kind):
    """One template by id, or None."""
    wanted = str(kind or '').strip().lower()
    for candidate in TEMPLATES:
        if candidate['id'] == wanted:
            return dict(candidate)
    return None


def request_policy():
    """The numbers every outbound Connection request runs under, for the surfaces that explain them."""
    from .connections import (REQUEST_ATTEMPTS, REQUEST_BUDGET, RETRY_BACKOFF, RETRY_STATUSES,
                              TEST_TIMEOUT)
    return {
        'attempts': REQUEST_ATTEMPTS,
        'timeout': TEST_TIMEOUT,
        'budget': REQUEST_BUDGET,
        'backoff': RETRY_BACKOFF,
        'retry_statuses': list(RETRY_STATUSES),
        'note': ('Kel reads only the status and never keeps the body. It tries again when a service is '
                 'busy or a connection drops, never when the service has answered.'),
    }
