"""Connection actions (V2.0 / V2-04): the things Kel can do with a service, as data.

An action is one row: what it is called, the request it makes, what it gives back, and whether it changes
anything. Nothing here is a code path per service — `connections.run()` reads a row and makes the request
through the same choke point as everything else, so a service Nick added by hand can have actions written
the same way, and V2-14's network rules still cover every one of them.

Rules this file exists to keep:

- **Only documented addresses.** Every `path` below is the one the service's own documentation publishes.
  Where Kel does not know a service's addresses (Raptive) or the service cannot work without an account
  sign-in step that is not built yet (Google Drive), there are no actions rather than invented ones.
- **`mutating` is honest.** A row that changes something in Nick's account must say so, and `run()` refuses
  it unless Nick confirmed. Today every action here is a read, so nothing Kel can do changes anything.
- **No payloads.** An action's answer goes back to the caller and is never written down; what is recorded is
  that the action ran — see `connections.events()`.
"""

# Every row: id, service (the catalogue id it belongs to), name, description, method, path (relative to the
# service's API address), params Nick may pass, returns, mutating, source.
ACTIONS = (
    {
        'id': 'github-whoami',
        'service': 'github',
        'name': 'See which account the token belongs to',
        'description': 'Asks GitHub who the stored token is, so you can tell which account Kel is using.',
        'method': 'GET',
        'path': '/user',
        'params': (),
        'returns': 'Your login name, name and public profile count.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'github-notifications',
        'service': 'github',
        'name': 'Read your unread notifications',
        'description': 'The notifications GitHub shows you when you sign in.',
        'method': 'GET',
        'path': '/notifications',
        'params': ('per_page',),
        'returns': 'The unread notifications, newest first.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'stripe-account',
        'service': 'stripe',
        'name': "Read your Stripe account",
        'description': 'The account details behind the stored secret key.',
        'method': 'GET',
        'path': '/v1/account',
        'params': (),
        'returns': 'The account id, country, currency and payout settings.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'stripe-customers',
        'service': 'stripe',
        'name': 'List your Stripe customers',
        'description': 'The customers on the account, as Stripe lists them.',
        'method': 'GET',
        'path': '/v1/customers',
        'params': ('limit',),
        'returns': 'A page of customers.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'figma-whoami',
        'service': 'figma',
        'name': 'See which Figma account the token belongs to',
        'description': 'Asks Figma who the stored token is.',
        'method': 'GET',
        'path': '/v1/me',
        'params': (),
        'returns': 'Your Figma handle and email.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'clickup-whoami',
        'service': 'clickup',
        'name': 'See which ClickUp user the token belongs to',
        'description': 'Asks ClickUp who the stored token is.',
        'method': 'GET',
        'path': '/user',
        'params': (),
        'returns': 'Your ClickUp user, and the workspaces the token can see.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'discord-whoami',
        'service': 'discord',
        'name': 'See which Discord bot the token belongs to',
        'description': 'Asks Discord which bot the stored token belongs to.',
        'method': 'GET',
        'path': '/users/@me',
        'params': (),
        'returns': 'The bot account behind the token.',
        'mutating': False,
        'source': 'documented',
    },
    {
        'id': 'pitcher-list-recent-posts',
        'service': 'pitcher-list',
        'name': 'Read the latest Pitcher List posts',
        'description': 'The newest posts from the site, through its WordPress interface.',
        'method': 'GET',
        'path': '/wp/v2/posts',
        'params': ('per_page',),
        'returns': 'The newest posts, newest first.',
        'mutating': False,
        'source': 'assumed',
    },
    {
        'id': 'gdrive-files',
        'service': 'google-drive',
        'name': 'List your Drive files',
        'description': 'The files in your Drive, through the account sign-in Kel keeps for Google.',
        'method': 'GET',
        'path': '/files?pageSize=10&fields=files(id,name,mimeType),nextPageToken',
        'params': (),
        'returns': 'Up to ten files with their names and types.',
        'mutating': False,
        'source': 'documented',
        # V2-04b: the permission this action needs — refused in plain words when not granted.
        'scopes': ('https://www.googleapis.com/auth/drive.metadata.readonly',),
    },
)


def actions():
    """Every action, as rows."""
    return [dict(action) for action in ACTIONS]


def actions_for(service_id):
    """The actions that belong to one known service. No service name is ever branched on."""
    wanted = str(service_id or '').strip().lower()
    return [dict(action) for action in ACTIONS if action['service'] == wanted]


def action(action_id):
    """One action by id, or None."""
    wanted = str(action_id or '').strip().lower()
    for candidate in ACTIONS:
        if candidate['id'] == wanted:
            return dict(candidate)
    return None
