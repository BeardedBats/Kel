"""Scheduled tasks as scheduled Recipes (D-57).

A schedule is a trigger, not a new kind of work: each firing becomes an ordinary submission (the
D-53 hand-off) and so an ordinary job, and Work, Activity, Needs you, the card, Retry, Stop and "Why
this model?" come for free. Run history is folded from the schedule's own events plus the
submissions and jobs it started — there is no run table.

- Cadences: `manual` (Run now only), `cron` (a standard 5-field expression, parsed here with the
  standard library), `interval` (every N minutes, anchored to when the schedule was made) and `once`.
  Times are evaluated in the schedule's IANA time zone, or this computer's zone when it has none (or
  when no time zone database is available). A wall time that a DST jump skips runs at the first valid
  minute after it; a wall time that happens twice runs once.
- Firing runs inside the engine's supervision loop (`Service._tick`, at most every 5 s), never while
  Kel is restarting for an update. A due slot is claimed with a compare-and-set on `next_due_at`, and
  every run event carries `dedupe='schedule:<id>:<slot>'`, so a slot never fires twice.
- Missed runs (Kel closed or asleep): only the newest missed slot runs, and only if it is at most
  min(12 h, the cadence's own gap) late; the older ones are recorded once as "Missed N runs".
- "Skip if still running" means exactly that; otherwise one coalesced run waits for the last to end.
- A schedule whose recipe, project or conversation is gone gets a `problem`, is paused, and shows in
  Needs you.
"""
import contextlib
from datetime import date, datetime, timedelta
import json
import math
import secrets
import threading
import time
import uuid

from .core import PolicyError, encode, uid


MIGRATION_VERSION = 33
MIGRATION_NAME = 'v2-schedules'

DDL = """
CREATE TABLE IF NOT EXISTS schedules(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, project_id TEXT NOT NULL,
  target TEXT NOT NULL, cadence TEXT NOT NULL,
  timezone TEXT, start_mode TEXT NOT NULL,
  conversation_id TEXT, model TEXT, skip_if_running INTEGER NOT NULL DEFAULT 1,
  enabled INTEGER NOT NULL DEFAULT 1, next_due_at REAL, queued_slot REAL, last_slot REAL,
  zone_sig TEXT, problem TEXT, origin TEXT UNIQUE,
  created REAL NOT NULL, updated REAL NOT NULL, deleted REAL);
CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(next_due_at) WHERE enabled=1 AND deleted IS NULL;
CREATE TABLE IF NOT EXISTS schedule_conversations(conversation_id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL,
  created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS conversation_hidden(conversation_id TEXT PRIMARY KEY, reason TEXT, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS schedule_meta(key TEXT PRIMARY KEY, value TEXT, at REAL NOT NULL)
"""

TICK_SECONDS = 5
MIN_INTERVAL_MINUTES = 5
MAX_INTERVAL_MINUTES = 366 * 24 * 60
MISSED_WINDOW = 12 * 3600
MAX_SLOTS = 100000
CLOCK_JUMP = 90
IMPORTED_RUNS = 20
OPEN_EXCLUDED = ('CLOSED', 'CANCELLED')
START_MODES = ('new_conversation', 'existing')
LOCAL_ZONE_LABEL = "This computer's time zone"
ACK = "Scheduled run of “%s” started. I'll post the result here once it has been checked."
NO_FOLDER = ("This task asks for a code change, but its project has no folder yet. Set the project's folder "
             'and test command in Projects, then run it again.')

MONTH_NAMES = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')
DOW_NAMES = ('SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT')
DAY_WORDS = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
SHORT_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
SHORT_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MACROS = {'@hourly': '0 * * * *', '@daily': '0 0 * * *', '@midnight': '0 0 * * *',
          '@weekly': '0 0 * * 0', '@monthly': '0 0 1 * *', '@yearly': '0 0 1 1 *', '@annually': '0 0 1 1 *'}


def ensure_schema(store):
    """Migration 33 through the ledger: the schedules table and its side tables. Idempotent."""
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)')
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return False
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'Scheduled tasks (D-57): schedules, their run chats, hidden chats'))
    return True


def hidden_ids(db):
    """Conversation ids hidden because the schedule that made them was deleted (read inside `db`)."""
    try:
        return {row[0] for row in db.execute('SELECT conversation_id FROM conversation_hidden')}
    except Exception:
        return set()


def scheduled_conversations(db):
    """conversation id -> the schedule whose run created it."""
    try:
        return {row[0]: row[1] for row in db.execute('SELECT conversation_id,schedule_id FROM schedule_conversations')}
    except Exception:
        return {}


# -- time zones -------------------------------------------------------------------------------------
def _zone(name):
    """The ZoneInfo for an IANA name, or None (this computer's zone) when unknown or unavailable."""
    if not name:
        return None
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return None


def _zone_database():
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo('Europe/London')
        return True
    except Exception:
        return False


def validate_timezone(name):
    if name in (None, ''):
        return None
    if not isinstance(name, str) or len(name) > 64:
        raise PolicyError("Kel doesn't know that time zone.")
    name = name.strip()
    if _zone(name) is None and _zone_database():
        raise PolicyError("Kel doesn't know the time zone “%s”." % name)
    return name  # without a time zone database the run uses this computer's zone


def zone_label(name):
    return name if name and _zone(name) is not None else LOCAL_ZONE_LABEL


def zone_signature(name):
    zone = _zone(name)
    if zone is not None:
        return 'iana:' + name
    now = datetime.now().astimezone()
    return 'local:%s:%s' % (now.tzname(), now.utcoffset())


def _to_wall(ts, zone):
    if zone is None:
        return datetime.fromtimestamp(ts)
    return datetime.fromtimestamp(ts, zone).replace(tzinfo=None)


def _from_wall(wall, zone, fold=0):
    if zone is None:
        return wall.replace(fold=fold).timestamp()
    return wall.replace(tzinfo=zone, fold=fold).timestamp()


def _valid_wall(wall, zone):
    return _to_wall(_from_wall(wall, zone), zone).replace(fold=0) == wall.replace(fold=0)


def _resolve(wall, zone):
    """The instant a wall-clock minute names: its first occurrence in a fold; in a DST gap, the first
    valid minute after it."""
    if _valid_wall(wall, zone):
        return _from_wall(wall, zone, 0)
    probe = wall
    for _ in range(24 * 60):
        probe += timedelta(minutes=1)
        if _valid_wall(probe, zone):
            return _from_wall(probe, zone, 0)
    return None


# -- cron -------------------------------------------------------------------------------------------
class CronSpec:
    def __init__(self, minutes, hours, doms, months, dows, dom_star, dow_star):
        self.minutes = sorted(minutes)
        self.hours = sorted(hours)
        self.doms = set(doms)
        self.months = set(months)
        self.dows = set(dows)
        self.dom_star = dom_star
        self.dow_star = dow_star

    def day_matches(self, day):
        if day.month not in self.months:
            return False
        dow = (day.weekday() + 1) % 7
        if self.dom_star and self.dow_star:
            return True
        if self.dom_star:
            return dow in self.dows
        if self.dow_star:
            return day.day in self.doms
        return day.day in self.doms or dow in self.dows  # Vixie: both restricted → either matches


def _cron_value(text, names, offset):
    text = text.strip().upper()
    if text.isdigit():
        return int(text)
    if names and text in names:
        return names.index(text) + offset
    raise ValueError(text)


def _cron_field(text, low, high, names=None, offset=0):
    values = set()
    for part in text.split(','):
        if not part:
            raise ValueError(text)
        base, step = part, 1
        if '/' in part:
            base, raw = part.split('/', 1)
            if not raw.isdigit() or int(raw) < 1:
                raise ValueError(part)
            step = int(raw)
        if base == '*':
            first, last = low, high
        elif '-' in base:
            left, right = base.split('-', 1)
            first, last = _cron_value(left, names, offset), _cron_value(right, names, offset)
        else:
            first = _cron_value(base, names, offset)
            last = high if '/' in part else first
        if first < low or last > high or first > last:
            raise ValueError(part)
        values.update(range(first, last + 1, step))
    return values


def parse_cron(expr):
    """A CronSpec for a standard 5-field expression (minute hour day-of-month month day-of-week)."""
    if not isinstance(expr, str) or not expr.strip() or len(expr) > 200:
        raise PolicyError('Choose when this task should run.')
    text = MACROS.get(expr.strip().lower(), expr)
    fields = text.split()
    if len(fields) != 5:
        raise PolicyError('A custom schedule needs five parts: minute, hour, day of month, month and '
                          'day of week.')
    try:
        minutes = _cron_field(fields[0], 0, 59)
        hours = _cron_field(fields[1], 0, 23)
        doms = _cron_field(fields[2], 1, 31)
        months = _cron_field(fields[3], 1, 12, MONTH_NAMES, 1)
        dows = {value % 7 for value in _cron_field(fields[4], 0, 7, DOW_NAMES, 0)}
    except ValueError:
        raise PolicyError('Kel could not read that custom schedule.') from None
    return CronSpec(minutes, hours, doms, months, dows, fields[2].startswith('*'), fields[4].startswith('*'))


def _cron_min_gap(spec):
    """The shortest gap in minutes between two runs of a cron schedule (within or across hours)."""
    minutes = spec.minutes
    gaps = [b - a for a, b in zip(minutes, minutes[1:])]
    hours = set(spec.hours)
    if any((hour + 1) % 24 in hours for hour in hours):
        gaps.append(60 - minutes[-1] + minutes[0])
    return min(gaps) if gaps else None


def _cron_next(spec, zone, after):
    start = _to_wall(after, zone).replace(second=0, microsecond=0, fold=0) + timedelta(minutes=1)
    day = start.date()
    for _ in range(366 * 8 + 2):  # eight years: long enough for 29 February on any weekday
        if spec.day_matches(day):
            for hour in spec.hours:
                if day == start.date() and hour < start.hour:
                    continue
                for minute in spec.minutes:
                    wall = datetime(day.year, day.month, day.day, hour, minute)
                    if wall < start:
                        continue
                    at = _resolve(wall, zone)
                    if at is not None and at > after:
                        return at
        day += timedelta(days=1)
    return None


# -- cadences ---------------------------------------------------------------------------------------
def _instant(value, tz):
    """Epoch seconds from a number or an ISO 8601 string (a naive one is read in the schedule's zone)."""
    if isinstance(value, bool):
        raise PolicyError('Choose the date and time this task should run.')
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            moment = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except ValueError:
            raise PolicyError('Choose the date and time this task should run.') from None
        if moment.tzinfo is None:
            return _from_wall(moment, _zone(tz))
        return moment.timestamp()
    raise PolicyError('Choose the date and time this task should run.')


def normalize_cadence(cadence, tz=None, now=None, *, future=True):
    """The stored form of a cadence, or PolicyError in plain words (interval >= 5 minutes, a one-off
    time in the future, a cron that runs at most every 5 minutes and comes round at all)."""
    now = time.time() if now is None else now
    if not isinstance(cadence, dict):
        raise PolicyError('Choose when this task should run.')
    kind = cadence.get('kind')
    if kind == 'manual':
        return {'kind': 'manual'}
    if kind == 'interval':
        minutes = cadence.get('minutes')
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not math.isfinite(minutes) \
                or int(minutes) != minutes:
            raise PolicyError('Choose how many minutes apart this task should run.')
        minutes = int(minutes)
        if minutes < MIN_INTERVAL_MINUTES:
            raise PolicyError('A scheduled task can run at most every %d minutes.' % MIN_INTERVAL_MINUTES)
        if minutes > MAX_INTERVAL_MINUTES:
            raise PolicyError('A scheduled task has to run at least once a year.')
        return {'kind': 'interval', 'minutes': minutes}
    if kind == 'once':
        at = _instant(cadence.get('at'), tz)
        if future and at <= now:
            raise PolicyError('That time has already passed. Choose a time in the future.')
        return {'kind': 'once', 'at': at}
    if kind == 'cron':
        expr = ' '.join(str(cadence.get('expr') or '').split())
        spec = parse_cron(expr)
        gap = _cron_min_gap(spec)
        if gap is not None and gap < MIN_INTERVAL_MINUTES:
            raise PolicyError('A scheduled task can run at most every %d minutes.' % MIN_INTERVAL_MINUTES)
        if _cron_next(spec, _zone(tz), now) is None:
            raise PolicyError('That schedule never comes round. Choose another day or time.')
        return {'kind': 'cron', 'expr': expr}
    raise PolicyError('Choose when this task should run.')


def next_after(cadence, tz, after, created=None):
    """The first slot strictly after `after` (epoch seconds), or None when there is none."""
    kind = (cadence or {}).get('kind')
    if kind == 'once':
        at = cadence.get('at')
        return at if at is not None and at > after else None
    if kind == 'interval':
        step = cadence['minutes'] * 60.0
        anchor = created if created is not None else after
        count = max(1, math.floor((after - anchor) / step) + 1)
        slot = anchor + count * step
        while slot <= after:
            count += 1
            slot = anchor + count * step
        return slot
    if kind == 'cron':
        return _cron_next(parse_cron(cadence['expr']), _zone(tz), after)
    return None


def _clock(hour, minute):
    suffix = 'AM' if hour < 12 else 'PM'
    return '%d:%02d %s' % (hour % 12 or 12, minute, suffix)


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        return '%dth' % n
    return '%d%s' % (n, {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


def _join(words):
    words = list(words)
    if len(words) <= 1:
        return ''.join(words)
    return ', '.join(words[:-1]) + ' and ' + words[-1]


def local_time(ts, tz, with_date=True):
    """'Mon 12 Oct, 9:00 AM' in the schedule's zone (no platform-specific strftime flags)."""
    wall = _to_wall(ts, _zone(tz))
    clock = _clock(wall.hour, wall.minute)
    if not with_date:
        return clock
    return '%s %d %s, %s' % (SHORT_DAYS[wall.weekday()], wall.day, SHORT_MONTHS[wall.month - 1], clock)


def _step_of(values, low, high):
    """k when values == range(low, high+1, k), else None."""
    values = sorted(values)
    if len(values) < 2 or values[0] != low:
        return None
    step = values[1] - values[0]
    return step if values == list(range(low, high + 1, step)) else None


def describe(cadence, tz=None):
    """One plain sentence for a cadence ("Every weekday at 9:00 AM")."""
    kind = (cadence or {}).get('kind')
    if kind == 'manual':
        return 'Only when you run it'
    if kind == 'once':
        return 'Once, on ' + local_time(cadence['at'], tz).replace(', ', ' at ', 1)
    if kind == 'interval':
        minutes = cadence['minutes']
        if minutes % 1440 == 0:
            days = minutes // 1440
            return 'Every day' if days == 1 else 'Every %d days' % days
        if minutes % 60 == 0:
            hours = minutes // 60
            return 'Every hour' if hours == 1 else 'Every %d hours' % hours
        return 'Every %d minutes' % minutes
    if kind != 'cron':
        return 'On a schedule'
    try:
        spec = parse_cron(cadence['expr'])
    except PolicyError:
        return 'On a custom schedule'
    every_day = spec.dom_star and spec.dow_star and len(spec.months) == 12
    all_hours = len(spec.hours) == 24
    if every_day and all_hours:
        step = _step_of(spec.minutes, 0, 59)
        if step:
            return 'Every %d minutes' % step
        if len(spec.minutes) == 1:
            minute = spec.minutes[0]
            return 'Every hour, on the hour' if minute == 0 else 'Every hour at %d minutes past' % minute
    if every_day and len(spec.minutes) == 1 and len(spec.hours) > 1:
        step = _step_of(spec.hours, 0, 23)
        if step:
            minute = spec.minutes[0]
            return 'Every %d hours' % step + ('' if minute == 0 else ' at %d minutes past' % minute)
    if len(spec.minutes) != 1 or len(spec.hours) > 4 or len(spec.months) != 12:
        return 'On a custom schedule'
    times = _join(_clock(hour, spec.minutes[0]) for hour in spec.hours)
    if spec.dom_star and spec.dow_star:
        return 'Every day at ' + times
    if spec.dom_star:
        days = sorted(spec.dows)
        if days == [1, 2, 3, 4, 5]:
            return 'Every weekday at ' + times
        if days == [0, 6]:
            return 'Every Saturday and Sunday at ' + times
        order = sorted(days, key=lambda d: (d + 6) % 7)  # Monday first
        return 'Every %s at %s' % (_join(DAY_WORDS[d] for d in order), times)
    if spec.dow_star:
        doms = sorted(spec.doms)
        return 'On the %s of every month at %s' % (_join(_ordinal(d) for d in doms), times)
    return 'On a custom schedule'


def upcoming(cadence, tz, after, created=None, count=3):
    out = []
    cursor = after
    for _ in range(max(0, min(int(count or 3), 10))):
        slot = next_after(cadence, tz, cursor, created)
        if slot is None:
            break
        out.append(slot)
        cursor = slot
    return out


def instruction_refusal(text, root):
    """Why a scheduled instruction cannot run in a project, in plain words; None when it can.

    A scheduled run never creates a new project (no greenfield), and a code change needs the
    project's folder."""
    from .router import file_action
    from .service import CODING_VERBS
    lower = str(text or '').lower().strip()
    if lower.startswith(CODING_VERBS) and not root and not file_action(text):
        return NO_FOLDER
    return None


class Scheduler:
    """The schedules of one Data root, their API, and the firing pass run from `Service._tick`."""

    def __init__(self, service):
        self.service = service
        self.store = service.store
        ensure_schema(self.store)
        self.lock = threading.RLock()  # one firing pass at a time (supervision vs Run now)
        self._last_pass = 0.0
        self._clock = None

    # -- storage helpers ------------------------------------------------------------------------
    def _event(self, db, schedule_id, action, detail=None, dedupe=None, at=None):
        """One `schedule.<action>` event; False when its dedupe key already exists."""
        aggregate = 'schedule:' + schedule_id
        if dedupe and db.execute('SELECT 1 FROM events WHERE dedupe=?', (dedupe,)).fetchone():
            return False
        revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM events WHERE aggregate_id=?',
                              (aggregate,)).fetchone()[0]
        payload = {'schema_version': 1, 'schedule': {'id': schedule_id, 'action': action},
                   'detail': detail or {}}
        db.execute('INSERT INTO events(id,aggregate_id,revision,type,at,payload,dedupe) VALUES(?,?,?,?,?,?,?)',
                   (uid(), aggregate, revision, 'schedule.' + action, time.time() if at is None else at,
                    encode(payload), dedupe))
        return True

    def _row(self, schedule_id, db=None, deleted=False):
        if not isinstance(schedule_id, str) or not schedule_id:
            raise PolicyError('Pick a scheduled task first.')
        if db is None:
            with contextlib.closing(self.store.connect()) as own:
                row = own.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,)).fetchone()
        else:
            row = db.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,)).fetchone()
        if not row or (row['deleted'] and not deleted):
            raise PolicyError('That scheduled task no longer exists.')
        return dict(row)

    @staticmethod
    def _loads(row):
        out = dict(row)
        for key in ('target', 'cadence', 'model'):
            try:
                out[key] = json.loads(out[key]) if out.get(key) else None
            except (TypeError, ValueError):
                out[key] = None
        return out

    def _detail(self, row, **extra):
        detail = {'project_id': row['project_id'], 'name': row['name']}
        detail.update(extra)
        return detail

    # -- validation -----------------------------------------------------------------------------
    def _project(self, project_id):
        if not isinstance(project_id, str) or not project_id:
            raise PolicyError('Choose a project first.')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
            meta = db.execute('SELECT kind,archived FROM project_meta WHERE project_id=?',
                              (project_id,)).fetchone() if row else None
            tests = db.execute('SELECT command FROM project_tests WHERE project_id=?',
                               (project_id,)).fetchone() if row else None
        if not row:
            raise PolicyError('The project this task belongs to no longer exists.')
        if meta and meta['kind'] == 'system':
            raise PolicyError("That folder is Kel's own working space, not a project.")
        if meta and meta['archived']:
            raise PolicyError('The project this task belongs to is archived. Restore it in Projects first.')
        return dict(row), (json.loads(tests['command']) if tests else None)

    def _target(self, target, project_id, root, tests):
        if not isinstance(target, dict):
            raise PolicyError('Choose what this task should do.')
        kind = target.get('kind')
        if kind == 'instruction':
            text = target.get('text')
            text = text.strip() if isinstance(text, str) else ''
            if not text or len(text) > 20000:
                raise PolicyError('Write what Kel should do (up to 20,000 characters).')
            refusal = instruction_refusal(text, root)
            if refusal:
                raise PolicyError(refusal)
            return {'kind': 'instruction', 'text': text}
        if kind == 'recipe':
            from .recipes import RecipeLibrary, compile_recipe
            recipe_id = target.get('recipe_id')
            inputs = target.get('inputs') or {}
            if not isinstance(recipe_id, str) or not recipe_id:
                raise PolicyError('Choose a recipe first.')
            if not isinstance(inputs, dict):
                raise PolicyError('That recipe input is not valid.')
            try:
                info = RecipeLibrary(self.store).get(recipe_id, project_id=project_id)
            except PolicyError:
                raise PolicyError('The recipe this task runs is no longer available in this project.') from None
            recipe = info['recipe']
            needs_code = recipe['kind'] == 'coding' or any(
                step.get('kind_override') == 'coding' for step in recipe['steps'])
            if needs_code and not root:
                raise PolicyError(NO_FOLDER)
            compile_recipe(recipe, inputs, project_id, root=root, tests=tests)  # dry compile
            return {'kind': 'recipe', 'recipe_id': recipe_id, 'inputs': inputs}
        raise PolicyError('Choose what this task should do.')

    def _conversation(self, conversation_id, project_id):
        if not isinstance(conversation_id, str) or not conversation_id:
            raise PolicyError('Choose the conversation this task should post to.')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT project_id FROM conversations WHERE id=?', (conversation_id,)).fetchone()
            hidden = conversation_id in hidden_ids(db)
        if not row or hidden:
            raise PolicyError('The conversation this task posts to no longer exists.')
        if row['project_id'] != project_id:
            raise PolicyError('That conversation belongs to a different project.')
        return conversation_id

    @staticmethod
    def _model(model):
        if model in (None, '', {}):
            return None
        if not isinstance(model, dict):
            raise PolicyError('That model choice is not available in this version of Kel.')
        provider = model.get('provider')
        if not provider:
            return None
        from .model_prefs import ModelPrefs
        chosen = model.get('model') or None
        ModelPrefs._validate(provider, chosen)
        return {'provider': provider, 'model': chosen}

    def _validated(self, data, base=None, now=None):
        """The stored fields for a create (base None) or an update (base = the current row)."""
        base = base or {}
        now = time.time() if now is None else now

        def pick(key, default=None):
            return data[key] if key in data else base.get(key, default)
        name = pick('name')
        name = ' '.join(name.split()) if isinstance(name, str) else ''
        if not name or len(name) > 120:
            raise PolicyError('Give this task a name (up to 120 characters).')
        project_id = pick('project_id')
        project, tests = self._project(project_id)
        timezone = validate_timezone(pick('timezone'))
        cadence_changed = not base or 'cadence' in data or 'timezone' in data
        cadence = pick('cadence')
        cadence = normalize_cadence(cadence, timezone, now, future=cadence_changed) if cadence_changed \
            else cadence
        target = self._target(pick('target'), project_id, project['root'], tests)
        start_mode = pick('start_mode', 'new_conversation')
        if start_mode not in START_MODES:
            raise PolicyError('Choose whether each run starts a new conversation or posts to one you pick.')
        conversation_id = None
        if start_mode == 'existing':
            conversation_id = self._conversation(pick('conversation_id'), project_id)
        model = self._model(pick('model'))
        skip = pick('skip_if_running', True)
        enabled = pick('enabled', True)
        return {'name': name, 'project_id': project_id, 'target': target, 'cadence': cadence,
                'timezone': timezone, 'start_mode': start_mode, 'conversation_id': conversation_id,
                'model': model, 'skip_if_running': bool(skip), 'enabled': bool(enabled)}

    # -- API ------------------------------------------------------------------------------------
    def apply(self, data):
        action = data.get('action')
        if action == 'list':
            return self.list(data.get('project'))
        if action == 'get':
            if data.get('origin') and not data.get('id'):
                return self.get(origin=str(data['origin']))
            return self.get(data.get('id'))
        if action == 'create':
            return {'schedule': self.create(data)}
        if action == 'update':
            return {'schedule': self.update(data.get('id'), data)}
        if action == 'pause':
            return {'schedule': self.pause(data.get('id'))}
        if action == 'resume':
            return {'schedule': self.resume(data.get('id'))}
        if action == 'delete':
            return self.delete(data.get('id'), data.get('conversations') or 'keep')
        if action == 'run_now':
            return self.run_now(data.get('id'))
        if action == 'history':
            self._row(data.get('id'), deleted=True)
            return {'rows': self.history(data.get('id'), data.get('limit') or 50)}
        if action == 'preview':
            return self.preview(data.get('cadence'), data.get('timezone'), data.get('count') or 3)
        if action == 'import':
            return self.import_items(data.get('items'))
        if action == 'migration_status':
            return self.migration_status(data.get('record'))
        raise PolicyError('Unknown schedules action')

    def list(self, project=None):
        with contextlib.closing(self.store.connect()) as db:
            if project not in (None, '', '*'):
                rows = db.execute('SELECT * FROM schedules WHERE deleted IS NULL AND project_id=? ORDER BY created',
                                  (project,)).fetchall()
            else:
                rows = db.execute('SELECT * FROM schedules WHERE deleted IS NULL ORDER BY created').fetchall()
        items = [self.view(row) for row in rows]
        return {'schedules': items, 'needs_attention': sum(1 for item in items if item['problem'])}

    def get(self, schedule_id=None, origin=None):
        if origin is not None:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute('SELECT * FROM schedules WHERE origin=?', (origin,)).fetchone()
            if not row:
                raise PolicyError('That scheduled task no longer exists.')
            if row['deleted']:
                raise PolicyError('That scheduled task was deleted.')
            row = dict(row)
        else:
            row = self._row(schedule_id)
        return {'schedule': self.view(row), 'conversations': self._run_conversations(row['id'])}

    def view(self, row):
        from .model_prefs import model_label, provider_label
        item = self._loads(row)
        with contextlib.closing(self.store.connect()) as db:
            project = db.execute('SELECT name FROM projects WHERE id=?', (item['project_id'],)).fetchone()
            conversation = db.execute('SELECT title FROM conversations WHERE id=?',
                                      (item['conversation_id'],)).fetchone() if item['conversation_id'] else None
        target = dict(item['target'] or {})
        if target.get('kind') == 'recipe':
            try:
                from .recipes import RecipeLibrary
                target['recipe_name'] = RecipeLibrary(self.store).get(
                    target.get('recipe_id', ''), project_id=item['project_id'])['recipe']['name']
            except Exception:
                target['recipe_name'] = None
        model = item['model']
        label = 'Automatic'
        if model and model.get('provider'):
            label = model_label(model.get('model')) or provider_label(model['provider'])
        cadence = item['cadence'] or {'kind': 'manual'}
        history = self.history(item['id'], 5)
        last = next((h for h in history if h['status'] not in ('queued', 'coalesced')), None)
        if item['problem']:
            status = 'needs_attention'
        elif not item['enabled']:
            status = 'paused'
        elif cadence.get('kind') == 'once' and item['next_due_at'] is None:
            status = 'done'
        elif cadence.get('kind') == 'manual':
            status = 'manual'
        else:
            status = 'active'
        return {'id': item['id'], 'name': item['name'], 'project_id': item['project_id'],
                'project_name': project['name'] if project else None, 'target': target,
                'cadence': cadence, 'timezone': item['timezone'], 'timezone_label': zone_label(item['timezone']),
                'start_mode': item['start_mode'], 'conversation_id': item['conversation_id'],
                'conversation_title': conversation['title'] if conversation else None,
                'model': model, 'model_label': label, 'skip_if_running': bool(item['skip_if_running']),
                'enabled': bool(item['enabled']), 'status': status,
                'description': describe(cadence, item['timezone']),
                'next_due_at': item['next_due_at'] if item['enabled'] and not item['deleted'] else None,
                'running': self._running(item['id']), 'last_run': last, 'problem': item['problem'],
                'origin': item['origin'], 'created': item['created'], 'updated': item['updated']}

    def create(self, data):
        now = time.time()
        fields = self._validated(data, now=now)
        schedule_id = uid()
        next_due = next_after(fields['cadence'], fields['timezone'], now, now) if fields['enabled'] else None
        with self.store.transaction() as db:
            self._insert(db, schedule_id, fields, now, next_due, origin=None, problem=None)
            row = self._row(schedule_id, db)
            self._event(db, schedule_id, 'created', self._detail(row))
        self._wake()
        return self.view(self._row(schedule_id))

    def _insert(self, db, schedule_id, fields, now, next_due, origin, problem):
        db.execute('INSERT INTO schedules(id,name,project_id,target,cadence,timezone,start_mode,conversation_id,'
                   'model,skip_if_running,enabled,next_due_at,queued_slot,last_slot,zone_sig,problem,origin,'
                   'created,updated,deleted) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,?,?,?,NULL)',
                   (schedule_id, fields['name'], fields['project_id'], encode(fields['target']),
                    encode(fields['cadence']), fields['timezone'], fields['start_mode'], fields['conversation_id'],
                    encode(fields['model']) if fields['model'] else None, 1 if fields['skip_if_running'] else 0,
                    1 if fields['enabled'] else 0, next_due, zone_signature(fields['timezone']), problem, origin,
                    now, now))

    def update(self, schedule_id, data):
        now = time.time()
        with self.lock:
            row = self._loads(self._row(schedule_id))
            if row['problem'] and 'enabled' not in data:
                data = dict(data, enabled=True)  # Kel paused it for the problem this change fixes
            fields = self._validated(data, base=row, now=now)
            timing = any(key in data for key in ('cadence', 'timezone', 'enabled'))
            with self.store.transaction() as db:
                current = self._row(schedule_id, db)
                next_due = current['next_due_at']
                if timing or current['problem'] or (fields['enabled'] and next_due is None):
                    next_due = next_after(fields['cadence'], fields['timezone'], now, current['created']) \
                        if fields['enabled'] else None
                db.execute('UPDATE schedules SET name=?,project_id=?,target=?,cadence=?,timezone=?,start_mode=?,'
                           'conversation_id=?,model=?,skip_if_running=?,enabled=?,next_due_at=?,zone_sig=?,'
                           'problem=NULL,queued_slot=CASE WHEN ?=1 THEN queued_slot ELSE NULL END,updated=? '
                           'WHERE id=?',
                           (fields['name'], fields['project_id'], encode(fields['target']), encode(fields['cadence']),
                            fields['timezone'], fields['start_mode'], fields['conversation_id'],
                            encode(fields['model']) if fields['model'] else None,
                            1 if fields['skip_if_running'] else 0, 1 if fields['enabled'] else 0, next_due,
                            zone_signature(fields['timezone']), 1 if fields['enabled'] else 0, now, schedule_id))
                self._event(db, schedule_id, 'updated', self._detail(self._row(schedule_id, db)))
        self._wake()
        return self.view(self._row(schedule_id))

    def pause(self, schedule_id):
        with self.lock:
            with self.store.transaction() as db:
                row = self._row(schedule_id, db)
                db.execute('UPDATE schedules SET enabled=0,queued_slot=NULL,updated=? WHERE id=?',
                           (time.time(), schedule_id))
                if row['enabled']:
                    self._event(db, schedule_id, 'paused', self._detail(row, by='you'))
        return self.view(self._row(schedule_id))

    def resume(self, schedule_id):
        now = time.time()
        with self.lock:
            row = self._loads(self._row(schedule_id))
            cadence = row['cadence'] or {}
            if cadence.get('kind') == 'once' and (cadence.get('at') or 0) <= now:
                raise PolicyError('The time this task was set for has passed. Choose a new time to run it again.')
            self._validated({}, base=row, now=now)  # a problem still there is refused in its own words
            next_due = next_after(cadence, row['timezone'], now, row['created'])
            with self.store.transaction() as db:
                db.execute('UPDATE schedules SET enabled=1,problem=NULL,next_due_at=?,zone_sig=?,updated=? WHERE id=?',
                           (next_due, zone_signature(row['timezone']), now, schedule_id))
                self._event(db, schedule_id, 'resumed', self._detail(row))
        self._wake()
        return self.view(self._row(schedule_id))

    def delete(self, schedule_id, conversations='keep'):
        if conversations not in ('keep', 'delete'):
            raise PolicyError("Choose whether to keep this task's conversations.")
        now = time.time()
        with self.lock:
            with self.store.transaction() as db:
                row = self._row(schedule_id, db)
                db.execute('UPDATE schedules SET deleted=?,enabled=0,next_due_at=NULL,queued_slot=NULL,updated=? '
                           'WHERE id=?', (now, now, schedule_id))
                self._event(db, schedule_id, 'deleted', self._detail(row, conversations=conversations))
        hidden, kept = [], []
        if conversations == 'delete':
            open_ids = self._open_conversations()
            with self.store.transaction() as db:
                for (cid,) in db.execute('SELECT conversation_id FROM schedule_conversations WHERE schedule_id=?',
                                         (schedule_id,)).fetchall():
                    if cid in open_ids:
                        kept.append(cid)
                        continue
                    db.execute('INSERT OR IGNORE INTO conversation_hidden VALUES(?,?,?)',
                               (cid, 'schedule deleted: ' + schedule_id, now))
                    hidden.append(cid)
        return {'ok': True, 'id': schedule_id, 'hidden': hidden, 'kept_open': kept}

    def _open_conversations(self):
        """Conversations with work still open (a planning hand-off or a job not closed/cancelled)."""
        with contextlib.closing(self.store.connect()) as db:
            out = {row[0] for row in db.execute("SELECT conversation_id FROM submissions WHERE state='PLANNING'")}
        out.update(job.get('conversation') for job in self.store.list_jobs() if job.get('state') not in OPEN_EXCLUDED)
        return out

    def _run_conversations(self, schedule_id):
        with contextlib.closing(self.store.connect()) as db:
            hidden = hidden_ids(db)
            ids = [row[0] for row in db.execute(
                'SELECT conversation_id FROM schedule_conversations WHERE schedule_id=?', (schedule_id,))]
        ids = [cid for cid in ids if cid not in hidden]
        open_ids = self._open_conversations()
        return {'created': len(ids), 'open': sum(1 for cid in ids if cid in open_ids)}

    def run_now(self, schedule_id):
        with self.lock:
            row = self._loads(self._row(schedule_id))
            try:
                self._validated({}, base=row)
            except PolicyError as exc:
                self._set_problem(row, str(exc))
                raise
            out = self._fire(row, time.time(), 0.0, manual=True)
        if not out:
            raise PolicyError("Kel couldn't start this task. Its history says why.")
        return out

    def preview(self, cadence, tz=None, count=3):
        now = time.time()
        try:
            tz = validate_timezone(tz)
            normal = normalize_cadence(cadence, tz, now)
        except PolicyError as exc:
            return {'valid': False, 'message': str(exc), 'description': None, 'next': [],
                    'timezone_label': zone_label(tz if isinstance(tz, str) else None)}
        return {'valid': True, 'message': None, 'description': describe(normal, tz),
                'next': upcoming(normal, tz, now, now, count), 'timezone_label': zone_label(tz)}

    # -- migration of the donor scheduler (called by the main process only) ---------------------
    def migration_status(self, record=None):
        with self.store.transaction() as db:
            if record is not None:
                if not isinstance(record, dict):
                    raise PolicyError('A migration summary is required.')
                db.execute('INSERT INTO schedule_meta VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET '
                           'value=excluded.value,at=excluded.at', ('donor_migration', encode(record), time.time()))
            row = db.execute("SELECT value,at FROM schedule_meta WHERE key='donor_migration'").fetchone()
        if not row:
            return {'done': False, 'at': None, 'summary': None}
        return {'done': True, 'at': row['at'], 'summary': json.loads(row['value'])}

    def _lenient(self, item):
        """Storable fields for an import item that failed validation (it is imported paused)."""
        with contextlib.closing(self.store.connect()) as db:
            project_id = item.get('project_id')
            if not isinstance(project_id, str) or not db.execute('SELECT 1 FROM projects WHERE id=?',
                                                                 (project_id,)).fetchone():
                project_id = 'default'
            conversation_id = item.get('conversation_id') if isinstance(item.get('conversation_id'), str) else None
            if conversation_id and not db.execute('SELECT 1 FROM conversations WHERE id=? AND project_id=?',
                                                  (conversation_id, project_id)).fetchone():
                conversation_id = None
        name = item.get('name')
        name = ' '.join(name.split())[:120] if isinstance(name, str) and name.strip() else 'Scheduled task'
        target = item.get('target') if isinstance(item.get('target'), dict) else {}
        if target.get('kind') == 'recipe' and isinstance(target.get('recipe_id'), str):
            target = {'kind': 'recipe', 'recipe_id': target['recipe_id'],
                      'inputs': target.get('inputs') if isinstance(target.get('inputs'), dict) else {}}
        elif isinstance(target.get('text'), str) and target['text'].strip():
            target = {'kind': 'instruction', 'text': target['text'].strip()[:20000]}
        else:
            raise PolicyError('This task has nothing to run.')
        cadence = item.get('cadence') if isinstance(item.get('cadence'), dict) else {'kind': 'manual'}
        try:
            cadence = normalize_cadence(cadence, None, future=False)
        except PolicyError:
            if cadence.get('kind') == 'interval' and isinstance(cadence.get('minutes'), (int, float)) \
                    and not isinstance(cadence.get('minutes'), bool):
                cadence = {'kind': 'interval', 'minutes': max(MIN_INTERVAL_MINUTES, int(cadence['minutes']))}
            else:
                cadence = {'kind': 'manual'}
        timezone = item.get('timezone') if isinstance(item.get('timezone'), str) and len(item['timezone']) <= 64 \
            else None
        try:
            model = self._model(item.get('model'))
        except PolicyError:
            model = None
        return {'name': name, 'project_id': project_id, 'target': target, 'cadence': cadence,
                'timezone': timezone, 'start_mode': 'existing' if conversation_id else 'new_conversation',
                'conversation_id': conversation_id, 'model': model,
                'skip_if_running': bool(item.get('skip_if_running', True)), 'enabled': False}

    def import_items(self, items):
        """Bring donor tasks over, idempotent by `origin`; `next_due_at` counts from now (no replay)."""
        if not isinstance(items, list) or len(items) > 500:
            raise PolicyError('Nothing to import.')
        results = []
        for item in items:
            origin = item.get('origin') if isinstance(item, dict) else None
            if not isinstance(origin, str) or not origin or len(origin) > 200:
                results.append({'origin': origin, 'id': None, 'status': 'refused', 'problem': None,
                                'message': 'An imported task needs its original id.'})
                continue
            with contextlib.closing(self.store.connect()) as db:
                existing = db.execute('SELECT id,problem FROM schedules WHERE origin=?', (origin,)).fetchone()
            if existing:
                results.append({'origin': origin, 'id': existing['id'], 'status': 'exists',
                                'problem': existing['problem'], 'message': None})
                continue
            now = time.time()
            problem = item.get('problem') if isinstance(item.get('problem'), str) and item['problem'].strip() else None
            try:
                fields = self._validated(item, now=now)
            except PolicyError as exc:
                problem = problem or str(exc)
                try:
                    fields = self._lenient(item)
                except PolicyError as refused:
                    results.append({'origin': origin, 'id': None, 'status': 'refused', 'problem': None,
                                    'message': str(refused)})
                    continue
            if problem:
                fields['enabled'] = False
            next_due = next_after(fields['cadence'], fields['timezone'], now, now) if fields['enabled'] else None
            schedule_id = uid()
            try:
                with self.store.transaction() as db:
                    self._insert(db, schedule_id, fields, now, next_due, origin=origin, problem=problem)
                    row = self._row(schedule_id, db)
                    self._event(db, schedule_id, 'imported', self._detail(row, origin=origin, problem=problem),
                                dedupe='schedule:import:' + origin)
                    runs = item.get('runs') if isinstance(item.get('runs'), list) else []
                    for index, run in enumerate(runs[:IMPORTED_RUNS]):
                        if not isinstance(run, dict):
                            continue
                        at = run.get('at')
                        at = float(at) if isinstance(at, (int, float)) and not isinstance(at, bool) else now
                        cid = run.get('conversation_id') if isinstance(run.get('conversation_id'), str) else None
                        self._event(db, schedule_id, 'imported_run', self._detail(row, conversation=cid, slot=at),
                                    dedupe='schedule:%s:imported:%d' % (schedule_id, index), at=at)
            except Exception as exc:
                if 'UNIQUE' not in str(exc):
                    raise
                with contextlib.closing(self.store.connect()) as db:
                    existing = db.execute('SELECT id,problem FROM schedules WHERE origin=?', (origin,)).fetchone()
                results.append({'origin': origin, 'id': existing['id'] if existing else None, 'status': 'exists',
                                'problem': existing['problem'] if existing else None, 'message': None})
                continue
            results.append({'origin': origin, 'id': schedule_id,
                            'status': 'imported_paused' if problem else 'imported', 'problem': problem,
                            'message': None})
        self._wake()
        return {'results': results}

    # -- firing ---------------------------------------------------------------------------------
    def _wake(self):
        self._last_pass = 0.0

    def maybe_tick(self):
        """Called from `Service._tick`: a firing pass at most every TICK_SECONDS."""
        if time.time() - self._last_pass < TICK_SECONDS:
            return 0
        self._last_pass = time.time()
        return self.tick()

    def _clock_moved(self, now):
        mono = time.monotonic()
        last, self._clock = self._clock, (now, mono)
        if last is None:
            return False
        return abs((now - last[0]) - (mono - last[1])) > CLOCK_JUMP

    def tick(self, now=None):
        """One firing pass. Returns how many runs it started."""
        if self.service.draining:
            return 0
        now = time.time() if now is None else now
        started = 0
        with self.lock:
            moved = self._clock_moved(now)
            with contextlib.closing(self.store.connect()) as db:
                rows = [dict(r) for r in db.execute(
                    'SELECT * FROM schedules WHERE enabled=1 AND deleted IS NULL AND problem IS NULL')]
            for row in rows:
                if self.service.draining:
                    break
                try:
                    started += self._pass(self._loads(row), now, moved)
                except Exception:
                    continue  # one schedule's failure never stops the others
        return started

    def _pass(self, row, now, moved):
        started = 0
        signature = zone_signature(row['timezone'])
        if row['next_due_at'] is not None and row['next_due_at'] > now and (moved or row['zone_sig'] != signature):
            # The computer's zone or clock changed: count the next slot again from now.
            following = next_after(row['cadence'], row['timezone'], now, row['created'])
            with self.store.transaction() as db:
                db.execute('UPDATE schedules SET next_due_at=?,zone_sig=? WHERE id=? AND next_due_at IS ?',
                           (following, signature, row['id'], row['next_due_at']))
            row['next_due_at'] = following
        if row['queued_slot'] is not None and not self._running(row['id']):
            with self.store.transaction() as db:
                claimed = db.execute('UPDATE schedules SET queued_slot=NULL WHERE id=? AND queued_slot=? AND enabled=1',
                                     (row['id'], row['queued_slot'])).rowcount
            if claimed and self._fire(row, row['queued_slot'], max(0.0, now - row['queued_slot'])):
                started += 1
        if row['next_due_at'] is not None and row['next_due_at'] <= now:
            started += self._due(row, now)
        return started

    def _due(self, row, now):
        cadence, tz, created = row['cadence'], row['timezone'], row['created']
        first = row['next_due_at']
        newest, previous, count, following = first, None, 1, None
        while True:
            following = next_after(cadence, tz, newest, created)
            if following is None or following > now:
                break
            previous, newest, count = newest, following, count + 1
            if count >= MAX_SLOTS:
                following = next_after(cadence, tz, now, created)
                break
        gap = (following - newest) if following is not None else None
        window = min(MISSED_WINDOW, gap) if gap else MISSED_WINDOW
        late = max(0.0, now - newest)
        runs = late <= window
        missed = count - 1 + (0 if runs else 1)
        with self.store.transaction() as db:
            claimed = db.execute('UPDATE schedules SET next_due_at=?,last_slot=?,zone_sig=? '
                                 'WHERE id=? AND next_due_at=? AND enabled=1 AND deleted IS NULL',
                                 (following, newest, zone_signature(tz), row['id'], first)).rowcount
            if not claimed:
                return 0
            if missed:
                self._event(db, row['id'], 'missed',
                            self._detail(row, count=missed, first=first, last=previous if runs else newest,
                                         late_by=late),
                            dedupe='schedule:%s:missed:%d' % (row['id'], int(first)))
        if not runs:
            return 0
        if self._running(row['id']):
            with self.store.transaction() as db:
                if row['skip_if_running']:
                    self._event(db, row['id'], 'skipped', self._detail(row, slot=newest, late_by=late),
                                dedupe='schedule:%s:%d' % (row['id'], int(newest)))
                else:
                    db.execute('UPDATE schedules SET queued_slot=? WHERE id=?', (newest, row['id']))
                    self._event(db, row['id'], 'queued', self._detail(row, slot=newest, late_by=late),
                                dedupe='schedule:%s:%d:queued' % (row['id'], int(newest)))
            return 0
        return 1 if self._fire(row, newest, late) else 0

    def _latest_fired(self, schedule_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT payload FROM events WHERE aggregate_id=? AND type='schedule.fired' "
                             'ORDER BY seq DESC LIMIT 1', ('schedule:' + schedule_id,)).fetchone()
        if not row:
            return None
        try:
            return (json.loads(row['payload']) or {}).get('detail') or {}
        except (TypeError, ValueError):
            return None

    def _running(self, schedule_id):
        """True while the latest run is planning or its job is not closed/cancelled (a job waiting for
        the person counts)."""
        fired = self._latest_fired(schedule_id)
        if not fired or not fired.get('submission_id'):
            return False
        with contextlib.closing(self.store.connect()) as db:
            sub = db.execute('SELECT state,job_id FROM submissions WHERE id=?', (fired['submission_id'],)).fetchone()
        if not sub:
            return False
        if sub['state'] == 'PLANNING':
            return True
        if sub['job_id']:
            try:
                return self.store.get(sub['job_id']).get('state') not in OPEN_EXCLUDED
            except KeyError:
                return False
        return False

    def _set_problem(self, row, problem, slot=None):
        with self.store.transaction() as db:
            db.execute('UPDATE schedules SET problem=?,enabled=0,queued_slot=NULL,updated=? WHERE id=?',
                       (problem, time.time(), row['id']))
            if slot is not None:
                self._event(db, row['id'], 'not_started', self._detail(row, slot=slot, cause=problem),
                            dedupe='schedule:%s:%d' % (row['id'], int(slot)))
            self._event(db, row['id'], 'paused', self._detail(row, by='kel', problem=problem))

    def _fire(self, row, slot, late_by, manual=False):
        """Start one run: an ordinary submission in the schedule's conversation. None when it could
        not start (the reason is recorded; a missing recipe, project or conversation pauses it)."""
        service = self.service
        try:
            project, tests = self._project(row['project_id'])
            target = row['target'] or {}
            if target.get('kind') == 'recipe':
                from .recipes import RecipeLibrary
                try:
                    RecipeLibrary(self.store).get(target.get('recipe_id', ''), project_id=row['project_id'])
                except PolicyError:
                    raise PolicyError('The recipe this task runs is no longer available in this project.') from None
            if row['start_mode'] == 'existing':
                self._conversation(row['conversation_id'], row['project_id'])
        except PolicyError as exc:
            self._set_problem(row, str(exc), None if manual else slot)
            return None
        created = row['start_mode'] != 'existing'
        cid = str(uuid.uuid4()) if created else row['conversation_id']
        if manual:
            sid = 'sched-%s-m%s' % (row['id'][:8], secrets.token_hex(6))
            dedupe = 'schedule:%s:manual:%s' % (row['id'], sid)
        else:
            sid = 'sched-%s-%d' % (row['id'][:8], int(slot))
            dedupe = 'schedule:%s:%d' % (row['id'], int(slot))
        with self.store.transaction() as db:
            if not self._event(db, row['id'], 'fired',
                               self._detail(row, slot=slot, late_by=late_by, submission_id=sid, conversation=cid,
                                            created_conversation=created, manual=manual),
                               dedupe=dedupe):
                return None  # this slot already fired
        try:
            if created:
                title = '%s · %s' % (row['name'], local_time(slot, row['timezone']))
                service.context.conversation(row['project_id'], title=title[:120], conversation_id=cid)
                with self.store.transaction() as db:
                    db.execute('INSERT OR IGNORE INTO schedule_conversations VALUES(?,?,?)', (cid, row['id'], time.time()))
            origin = {'id': row['id'], 'name': row['name'], 'slot': slot, 'late_by': late_by,
                      'model': row['model'], 'manual': manual}
            if target.get('kind') == 'recipe':
                from .recipes import RecipeLibrary
                library = RecipeLibrary(self.store)
                recipe = library.get(target['recipe_id'], project_id=row['project_id'])['recipe']
                data = {'id': sid, 'conversation': cid, 'text': 'Run recipe ' + recipe['name'], 'kind': 'recipe',
                        'recipe': {'recipe_id': target['recipe_id'], 'inputs': target.get('inputs') or {}}}
                service.submit(data, origin=origin)
                library.mark(row['project_id'], target['recipe_id'], run=True)
            else:
                service.submit({'id': sid, 'conversation': cid, 'text': target.get('text', ''), 'kind': 'scheduled'},
                               origin=origin)
        except Exception as exc:
            cause = str(exc).strip() or type(exc).__name__
            with self.store.transaction() as db:
                self._event(db, row['id'], 'not_started', self._detail(row, slot=slot, cause=cause, submission_id=sid),
                            dedupe='schedule:%s:not_started:%s' % (row['id'], sid))
            return None
        return {'submission': sid, 'conversation': cid}

    # -- history --------------------------------------------------------------------------------
    def history(self, schedule_id, limit=50):
        """The run history, folded from this schedule's events and the submissions/jobs they started."""
        try:
            limit = max(1, min(int(limit or 50), 500))
        except (TypeError, ValueError):
            raise PolicyError('How many runs?') from None
        with contextlib.closing(self.store.connect()) as db:
            events = []
            for row in db.execute('SELECT type,at,payload FROM events WHERE aggregate_id=? ORDER BY seq',
                                  ('schedule:' + schedule_id,)):
                try:
                    detail = (json.loads(row['payload']) or {}).get('detail') or {}
                except (TypeError, ValueError):
                    detail = {}
                events.append((row['type'][len('schedule.'):], row['at'], detail))
            current = db.execute('SELECT queued_slot FROM schedules WHERE id=?', (schedule_id,)).fetchone()
            sids = [d.get('submission_id') for kind, _, d in events if kind == 'fired' and d.get('submission_id')]
            subs = {}
            for start in range(0, len(sids), 400):
                part = sids[start:start + 400]
                for sub in db.execute('SELECT id,state,error,job_id FROM submissions WHERE id IN (%s)'
                                      % ','.join('?' * len(part)), part):
                    subs[sub['id']] = dict(sub)
            pending = {row['job_id'] for row in db.execute("SELECT job_id FROM approvals WHERE status='PENDING'")}
        queued_now = current['queued_slot'] if current else None
        fired_slots = {d.get('slot') for kind, _, d in events if kind == 'fired'}
        failed_to_start = {d.get('submission_id'): d.get('cause') for kind, _, d in events
                           if kind == 'not_started' and d.get('submission_id')}
        fired_sids = {d.get('submission_id') for kind, _, d in events if kind == 'fired'} - {None}
        now = time.time()
        rows = []
        for kind, at, detail in events:
            base = {'at': at, 'slot': detail.get('slot'), 'late_by': detail.get('late_by'),
                    'conversation': detail.get('conversation'), 'job_id': None,
                    'submission_id': detail.get('submission_id'), 'status': None, 'label': None, 'cause': None}
            if kind == 'fired':
                base.update(self._run_status(subs.get(detail.get('submission_id')), at, now, pending,
                                             failed_to_start.get(detail.get('submission_id'))))
            elif kind == 'not_started':
                if detail.get('submission_id') in fired_sids:
                    continue  # shown on its run's own row
                base.update(status='not_started', label="Didn't start", cause=detail.get('cause'))
            elif kind == 'skipped':
                base.update(status='skipped', label='Skipped — the last run was still going')
            elif kind == 'queued':
                if detail.get('slot') in fired_slots:
                    continue
                if queued_now is not None and detail.get('slot') == queued_now:
                    base.update(status='queued', label='Waiting for the last run to finish')
                else:
                    base.update(status='coalesced', label='Folded into a later run')
            elif kind == 'missed':
                count = int(detail.get('count') or 1)
                base.update(status='missed', slot=detail.get('last'),
                            label='Missed %d run%s while Kel was closed' % (count, '' if count == 1 else 's'))
            elif kind == 'imported_run':
                base.update(status='imported', label='Ran before this update')
            else:
                continue
            rows.append(base)
        rows.sort(key=lambda item: item['at'] or 0, reverse=True)
        return rows[:limit]

    def _run_status(self, sub, fired_at, now, pending, start_failure):
        if start_failure and not sub:
            return {'status': 'not_started', 'label': "Didn't start", 'cause': start_failure}
        if not sub:
            if now - fired_at < 30:
                return {'status': 'running', 'label': 'Starting'}
            return {'status': 'not_started', 'label': "Didn't start",
                    'cause': 'Kel closed before this run began.'}
        if not sub['job_id']:
            if sub['state'] == 'PLANNING':
                return {'status': 'running', 'label': 'Starting'}
            if sub['state'] in ('FAILED', 'INTERRUPTED'):
                return {'status': 'not_started', 'label': "Didn't start", 'cause': sub['error']}
            if sub['state'] == 'CANCELLED':
                return {'status': 'stopped', 'label': 'Stopped'}
            return {'status': 'settled', 'label': 'Finished'}
        try:
            job = self.store.get(sub['job_id'])
        except KeyError:
            return {'status': 'not_started', 'label': "Didn't start", 'cause': 'The work record is missing.',
                    'job_id': sub['job_id']}
        state, verdict = job.get('state'), job.get('verdict')
        out = {'job_id': job['id']}
        if state == 'CLOSED':
            out.update(status='success', label='Success') if verdict == 'VERIFIED' else \
                out.update(status='needs_look', label='Finished — needs a look')
        elif state in ('CANCELLED', 'CANCELLING'):
            out.update(status='stopped', label='Stopped')
        elif state == 'AWAITING_USER' or job['id'] in pending:
            out.update(status='needs_you', label='Needs you')
        else:
            out.update(status='running', label='Running')
        return out
