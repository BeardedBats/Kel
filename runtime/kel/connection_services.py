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

# `credential` is what Nick has to go and get, in his words.
# `fields` (D-87) are the values the Connect form asks for, each with the service's own name for it; `name`
# is the credential field the engine reads (`auth_for` in connections.py). `where` is one short line naming
# where the value comes from, and `connect_label` the button for an account sign-in.
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
        'fields': ({'name': 'api_key', 'label': 'Personal access token', 'secret': True},),
        'where': 'GitHub → Settings → Developer settings → Personal access tokens',
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
        'fields': ({'name': 'api_key', 'label': 'Secret key', 'secret': True},),
        'where': 'Stripe Dashboard → Developers → API keys',
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
        'fields': ({'name': 'api_key', 'label': 'Personal access token', 'secret': True},),
        'where': 'Figma → Settings → Security → Personal access tokens',
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
        'fields': ({'name': 'api_key', 'label': 'API token', 'secret': True},),
        'where': 'ClickUp → Settings → Apps → API Token',
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
        'fields': ({'name': 'token', 'label': 'Bot token', 'secret': True},),
        'where': 'Discord Developer Portal → your app → Bot → Token',
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
        'credential': ('your own Google sign-in app — an OAuth client ID and secret of the "Desktop app" type '
                       'from Google Cloud Console. Then you choose Connect, sign in with Google in your browser, '
                       'and Kel keeps the token'),
        'fields': ({'name': 'client_id', 'label': 'OAuth client ID', 'secret': False},
                   {'name': 'client_secret', 'label': 'Client secret', 'secret': True}),
        'where': 'Google Cloud Console → APIs & Services → Credentials → OAuth client (Desktop app)',
        'connect_label': 'Connect with Google',
        'source': 'documented',
        'note': ('Kel can see the names and types of your Drive files — never their contents — and changes '
                 'nothing. Before Connect works, save the client ID as a credential named client_id and the '
                 'secret as one named client_secret. A pasted access token works too, but Google lets it '
                 'expire after about an hour.'),
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
        'credential': ('your Pitcher List username and a WordPress application password from your account, '
                       'saved as two credentials named username and password'),
        'fields': ({'name': 'username', 'label': 'Username', 'secret': False},
                   {'name': 'password', 'label': 'Application password', 'secret': True}),
        'where': 'Your WordPress profile → Application Passwords',
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
        'fields': ({'name': 'api_key', 'label': 'API key', 'secret': True},),
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
