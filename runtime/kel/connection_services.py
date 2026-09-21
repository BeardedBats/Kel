"""Known services (V2.0 / V2-03): what Kel already knows about the services Nick uses.

This is a **data** list, not a framework and not a set of per-service features. Every entry is the same
kind of row a Connection is, filled in the way the service's own documentation says to, so Nick can add
Pitcher List, Stripe, Raptive, Google Drive, GitHub, ClickUp, Figma or Discord in one click instead of
hunting for a URL and a header name. What Kel can *do* with a service is a tool (V2-04) and is nowhere in
this file.

Nothing here is code that branches on a service name: `connections.py` stays service-agnostic (it does not
know these names), the catalogue is read as rows, and a service Nick adds by hand works exactly the same
way as one he picks from this list.

`source` is honest about where each address came from:
- `documented` — the service publishes this endpoint and auth shape.
- `assumed`    — a pattern Kel is fairly sure of (the standard WordPress layout), which Nick can correct.
- `to-confirm` — Kel does not know the address; the service tells Nick when it issues the credential.
"""

# `credential` is what Nick has to go and get, in his words, shown before he is asked for a value.
KNOWN_SERVICES = (
    {
        'id': 'github',
        'name': 'GitHub',
        'kind': 'api_key',
        'base_url': 'https://api.github.com',
        'auth_method': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': 'Bearer ',
        'docs_url': 'https://docs.github.com/rest',
        'test_endpoint': 'https://api.github.com/user',
        'credential': 'a personal access token with the scopes you want Kel to have',
        'source': 'documented',
    },
    {
        'id': 'stripe',
        'name': 'Stripe',
        'kind': 'api_key',
        'base_url': 'https://api.stripe.com',
        'auth_method': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': 'Bearer ',
        'docs_url': 'https://docs.stripe.com/api',
        'test_endpoint': 'https://api.stripe.com/v1/account',
        'credential': 'a secret key from your Stripe account',
        'source': 'documented',
    },
    {
        'id': 'figma',
        'name': 'Figma',
        'kind': 'api_key',
        'base_url': 'https://api.figma.com',
        'auth_method': 'header',
        'auth_header': 'X-Figma-Token',
        'auth_prefix': '',
        'docs_url': 'https://www.figma.com/developers/api',
        'test_endpoint': 'https://api.figma.com/v1/me',
        'credential': 'a personal access token from your Figma settings',
        'source': 'documented',
    },
    {
        'id': 'clickup',
        'name': 'ClickUp',
        'kind': 'api_key',
        'base_url': 'https://api.clickup.com/api/v2',
        'auth_method': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': '',
        'docs_url': 'https://developer.clickup.com',
        'test_endpoint': 'https://api.clickup.com/api/v2/user',
        'credential': 'your personal ClickUp API token',
        'source': 'documented',
    },
    {
        'id': 'discord',
        'name': 'Discord',
        'kind': 'bot',
        'base_url': 'https://discord.com/api/v10',
        'auth_method': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': 'Bot ',
        'docs_url': 'https://discord.com/developers/docs',
        'test_endpoint': 'https://discord.com/api/v10/users/@me',
        'credential': 'the bot token for the Discord bot you want Kel to use',
        'source': 'documented',
    },
    {
        'id': 'google-drive',
        'name': 'Google Drive',
        'kind': 'oauth',
        # V2-04b: which sign-in provider this service authorizes through (connection_oauth.py).
        'oauth_provider': 'google',
        'base_url': 'https://www.googleapis.com/drive/v3',
        'auth_method': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': 'Bearer ',
        'docs_url': 'https://developers.google.com/drive/api/reference/rest/v3',
        'test_endpoint': 'https://www.googleapis.com/drive/v3/about?fields=user',
        'credential': 'account authorization — you sign in and Kel keeps the token',
        'source': 'documented',
        'note': 'Google Drive needs the account sign-in step before Kel can check it.',
    },
    {
        'id': 'pitcher-list',
        'name': 'Pitcher List',
        'kind': 'api_key',
        'base_url': 'https://pitcherlist.com/wp-json',
        'auth_method': 'basic',
        'auth_header': '',
        'auth_prefix': '',
        'docs_url': 'https://developer.wordpress.org/rest-api/',
        'test_endpoint': 'https://pitcherlist.com/wp-json/wp/v2/users/me',
        'credential': 'the WordPress application password from your Pitcher List account, with your username',
        'source': 'assumed',
        'note': 'Kel assumes the standard WordPress address; change it if Pitcher List gave you a different one.',
    },
    {
        'id': 'raptive',
        'name': 'Raptive',
        'kind': 'api_key',
        'base_url': '',
        'auth_method': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': '',
        'docs_url': '',
        'test_endpoint': '',
        'credential': 'the API credential from your Raptive account',
        'source': 'to-confirm',
        'note': "Raptive's API address comes with your credential — paste it here and Kel will check it.",
    },
)


def catalogue():
    """The known services, as rows — the same shape a Connection has, minus the personal parts."""
    return [dict(entry) for entry in KNOWN_SERVICES]


def entry(service_id):
    """One known service, or None. Used to prefill a new connection; never to decide behaviour."""
    wanted = str(service_id or '').strip().lower()
    for candidate in KNOWN_SERVICES:
        if candidate['id'] == wanted:
            return dict(candidate)
    return None
