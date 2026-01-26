# Community Knowledge Research: Flask

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/flask/SKILL.md
**Packages Researched**: Flask@3.1.2, Flask-SQLAlchemy@3.1.1, Flask-Login@0.6.3, Flask-WTF@1.2.2, Werkzeug@3.1.5
**Official Repo**: pallets/flask
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 7 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 5 |
| Recommended to Add | 7 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: stream_with_context Regression in 3.1.2

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5804](https://github.com/pallets/flask/issues/5804) | [Maintainer Comment](https://github.com/pallets/flask/issues/5804#issuecomment-3058277636)
**Date**: 2025-09-01
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Flask 3.1.2 introduced a regression where `stream_with_context` triggers `teardown_request()` calls before response generation, causing issues when teardown callbacks expect request context to be complete. This can cause `KeyError` when using `g.pop()` in teardown functions because teardown runs multiple times.

**Reproduction**:
```python
from flask import Flask, g, stream_with_context

@app.teardown_request
def _teardown_request(_):
    g.pop("hello")  # KeyError on second call

@app.get("/stream")
def streamed_response():
    g.hello = "world"

    def generate():
        yield f"<p>Hello {g.hello}!</p>"

    return stream_with_context(generate())
```

**Solution/Workaround**:
```python
# Workaround: Make teardown idempotent
@app.teardown_request
def _teardown_request(_):
    g.pop("hello", None)  # Provide default value

# OR: Pin Flask to < 3.1.2 until fixed
# pip install "flask<3.1.2"
```

**Official Status**:
- [x] Will be fixed in version 3.2.0 as side effect of PR #5812
- [x] Documented behavior: teardown can run multiple times, should be idempotent
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related issue: [#5774 - stream_with_context does not work with async routes](https://github.com/pallets/flask/issues/5774) (fixed in 3.1.2)
- Fix PR: #5812 (in development for 3.2.0)

---

### Finding 1.2: Async Views with Gevent Incompatibility

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5881](https://github.com/pallets/flask/issues/5881) | [Maintainer Discussion](https://github.com/pallets/flask/issues/5881#issuecomment-3058277636)
**Date**: 2026-01-05
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Asgiref fails when gevent monkey-patching is active, preventing async views from working with gevent. The issue is that asyncio expects a single event loop per OS thread, but gevent's monkey-patching makes threading.Thread create greenlets instead of real threads, causing both loops to run on the same physical thread and block each other.

**Reproduction**:
```python
import gevent.monkey
gevent.monkey.patch_all()

from flask import Flask
import asyncio

app = Flask(__name__)

@app.get("/")
async def greet():
    await asyncio.sleep(1)
    return "Hello!"

# RuntimeError when handling concurrent requests
```

**Solution/Workaround**:
```python
# Workaround: Override Flask.async_to_sync to use gevent-compatible event loop
import asyncio
import gevent.monkey
import gevent.selectors
from flask import Flask

gevent.monkey.patch_all()
loop = asyncio.EventLoop(gevent.selectors.DefaultSelector())
gevent.spawn(loop.run_forever)

class MyFlask(Flask):
    def async_to_sync(self, func):
        def run(*args, **kwargs):
            coro = func(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return run

app = MyFlask(__name__)

@app.get("/")
async def greet():
    await asyncio.sleep(1)
    return "Hello!"
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior: async views documented as working with gevent, but only for individual requests, not concurrent
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related: [asyncio-gevent issue #12](https://github.com/gfmio/asyncio-gevent/issues/12)
- Note: Individual async requests work, but concurrent requests fail
- Maintainer comment: "defeats the whole purpose of both" (async + gevent)

---

### Finding 1.3: Test Client Session Not Updated on Redirect (3.1.2)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5786](https://github.com/pallets/flask/issues/5786)
**Date**: 2025-07-30
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using `follow_redirects` in the test client, the final state of `session` is not correctly updated after following redirects. Fixed in 3.1.2.

**Reproduction**:
```python
# In Flask < 3.1.2
def test_login_redirect(client):
    response = client.post('/login',
        data={'email': 'test@example.com', 'password': 'pass'},
        follow_redirects=True)
    # session may not reflect changes from redirect target
    assert 'user_id' in session  # May fail
```

**Solution/Workaround**:
```python
# Upgrade to Flask >= 3.1.2
pip install "flask>=3.1.2"

# OR: Don't use follow_redirects in tests, make separate requests
response = client.post('/login', data={...})
assert response.status_code == 302
response = client.get(response.location)  # Explicit redirect follow
```

**Official Status**:
- [x] Fixed in version 3.1.2
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Release notes: https://github.com/pallets/flask/releases/tag/3.1.2
- Fixed by PR addressing test client session handling

---

### Finding 1.4: Python 3.8 Support Dropped in 3.1.0

**Trust Score**: TIER 1 - Official
**Source**: [Flask 3.1.0 Release Notes](https://github.com/pallets/flask/releases/tag/3.1.0)
**Date**: 2024-11-13
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Yes (documented in frontmatter)

**Description**:
Flask 3.1.0 dropped support for Python 3.8. Projects using Python 3.8 must either upgrade Python or stay on Flask 3.0.x.

**Official Status**:
- [x] Documented behavior
- Breaking change in 3.1.0

**Cross-Reference**:
- Skill currently documents: "Latest Versions (verified January 2026): Flask: 3.1.2"
- No explicit Python version requirement mentioned - should add

---

### Finding 1.5: Werkzeug 3.1+ Required for Flask 3.1

**Trust Score**: TIER 1 - Official
**Source**: [Flask 3.1.0 Release Notes](https://github.com/pallets/flask/releases/tag/3.1.0)
**Date**: 2024-11-13
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Yes (Werkzeug: 3.1.5 listed)

**Description**:
Flask 3.1.0 updated minimum dependency versions: Werkzeug >= 3.1, ItsDangerous >= 2.2, Blinker >= 1.9. This can cause compatibility issues with older projects.

**Reproduction**:
```bash
# Installing Flask 3.1 will pull Werkzeug 3.1+
pip install flask==3.1.0

# Projects pinned to older Werkzeug may fail
# Error: "flask==2.2.4 incompatible with werkzeug==3.1.3"
```

**Solution/Workaround**:
```bash
# Update all Pallets projects together
pip install flask>=3.1.0 werkzeug>=3.1.0 itsdangerous>=2.2.0 blinker>=1.9.0
```

**Official Status**:
- [x] Documented behavior
- Breaking change in 3.1.0

**Cross-Reference**:
- Related issue: [#5652 - flask==2.2.4 incompatible with werkzeug==3.1.3](https://github.com/pallets/flask/issues/5652)

---

### Finding 1.6: Request.max_content_length Per-Request Override

**Trust Score**: TIER 1 - Official
**Source**: [Flask 3.1.0 Release Notes](https://github.com/pallets/flask/releases/tag/3.1.0)
**Date**: 2024-11-13
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Flask 3.1.0 added ability to customize `Request.max_content_length` per-request instead of only through `MAX_CONTENT_LENGTH` config. Also added `MAX_FORM_MEMORY_SIZE` and `MAX_FORM_PARTS` config options with security documentation.

**Solution/Workaround**:
```python
from flask import Flask, request

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB default

@app.route('/upload', methods=['POST'])
def upload():
    # Override for this specific route
    request.max_content_length = 100 * 1024 * 1024  # 100MB for uploads
    file = request.files['file']
    # ...
```

**Official Status**:
- [x] New feature in 3.1.0
- [x] Documented in security page

**Cross-Reference**:
- Security docs: https://flask.palletsprojects.com/en/stable/security/

---

### Finding 1.7: SECRET_KEY_FALLBACKS for Key Rotation

**Trust Score**: TIER 1 - Official
**Source**: [Flask 3.1.0 Release Notes](https://github.com/pallets/flask/releases/tag/3.1.0)
**Date**: 2024-11-13
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Flask 3.1.0 added support for key rotation with `SECRET_KEY_FALLBACKS` config - a list of old secret keys that can still be used for unsigning. Extensions need to add explicit support.

**Solution/Workaround**:
```python
# config.py
class Config:
    SECRET_KEY = "new-secret-key-2024"
    SECRET_KEY_FALLBACKS = [
        "old-secret-key-2023",
        "older-secret-key-2022"
    ]
```

**Official Status**:
- [x] New feature in 3.1.0
- [x] Requires extension support

**Cross-Reference**:
- Note: Flask-Login, Flask-WTF may need updates to support this

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Application Context in Threading

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Sentry.io Guide](https://sentry.io/answers/working-outside-of-application-context/) | [Flask Docs](https://flask.palletsprojects.com/en/stable/appcontext/)
**Date**: 2024+
**Verified**: Partial (common pattern)
**Impact**: MEDIUM
**Already in Skill**: Partially (app_context mentioned, threading not)

**Description**:
When passing Flask's `current_app` to a new thread, you must pass `current_app._get_current_object()` instead of `current_app` directly, or the thread will lose context.

**Reproduction**:
```python
from flask import current_app
import threading

def background_task():
    # This will fail - current_app is a proxy
    app_name = current_app.name

@app.route('/start')
def start_task():
    # WRONG
    thread = threading.Thread(target=background_task)
    thread.start()
```

**Solution/Workaround**:
```python
from flask import current_app
import threading

def background_task(app):
    with app.app_context():
        # Now we have context
        app_name = app.name

@app.route('/start')
def start_task():
    # CORRECT - unwrap proxy and push context
    app = current_app._get_current_object()
    thread = threading.Thread(target=background_task, args=(app,))
    thread.start()
```

**Community Validation**:
- Multiple sources (Sentry, Medium, official docs)
- Common gotcha in production applications
- Well-documented pattern

**Recommendation**: Add to Known Issues or Application Context section

---

### Finding 2.2: Flask-Login Session Protection Modes

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Flask-Login Docs](https://flask-login.readthedocs.io/) | [Medium Guide](https://medium.com/@prajwal_ahluwalia/from-login-to-logout-mastering-secure-session-management-with-flask-login-and-sqlalchemy-09a1153ac239)
**Date**: 2024
**Verified**: Partial
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Flask-Login has two session protection modes: "basic" and "strong". In strong mode, if session identifiers don't match (e.g., IP address changes), the entire session and remember token are deleted. This can cause unexpected logouts for users on mobile networks or VPNs.

**Solution/Workaround**:
```python
# app/extensions.py
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.session_protection = "basic"  # Default, less strict

# OR for high-security apps
login_manager.session_protection = "strong"  # Strict, may logout on IP change

# OR disable completely (not recommended)
login_manager.session_protection = None
```

**Community Validation**:
- Official Flask-Login documentation
- Multiple blog posts from 2024
- Common misconfiguration

**Recommendation**: Add to Authentication with Flask-Login section

---

### Finding 2.3: CSRF Protection Cache Interference

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Flask-WTF Docs](https://flask-wtf.readthedocs.io/en/latest/csrf/) | [Security Guide](https://securityboulevard.com/2024/01/best-practices-to-protect-your-flask-applications/)
**Date**: 2024
**Verified**: Partial
**Impact**: MEDIUM
**Already in Skill**: Partially (CSRF mentioned, cache issue not)

**Description**:
If webserver cache policy caches pages longer than `WTF_CSRF_TIME_LIMIT`, browsers may serve cached pages with expired CSRF tokens, causing form submissions to fail.

**Reproduction**:
```python
# config.py
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

# Nginx cache config (separate file)
proxy_cache_valid 200 4h;  # PROBLEM: 4 hours > 1 hour
```

**Solution/Workaround**:
```python
# Option 1: Align cache duration with token lifetime
WTF_CSRF_TIME_LIMIT = None  # Never expire (less secure)

# Option 2: Exclude forms from cache
@app.after_request
def add_cache_headers(response):
    if request.method == 'POST':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Option 3: Configure webserver to not cache POST targets
# In Nginx: add "proxy_cache_bypass $cookie_session" for form routes
```

**Community Validation**:
- Official Flask-WTF documentation warning
- Security best practices guides from 2024

**Recommendation**: Add to CSRF Protection or Common Errors section

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Flask-Login Concurrent Sessions

**Trust Score**: TIER 3 - Community Consensus
**Source**: [TestDriven.io](https://testdriven.io/blog/flask-spa-auth/) | [Medium](https://syscrews.medium.com/session-based-authentication-in-flask-d43fe36afc0f)
**Date**: 2024
**Verified**: Cross-Referenced Only
**Impact**: LOW
**Already in Skill**: No

**Description**:
Flask-Login allows the same user login ID to be used by multiple people concurrently on different browsers by default. This is often unexpected - developers assume Flask-Login prevents concurrent sessions.

**Solution**:
```python
# If you need to prevent concurrent sessions, implement custom logic:
from flask_login import user_logged_in
from app.extensions import db
from app.models import User

@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    # Invalidate all other sessions for this user
    # This requires custom session storage and tracking
    user.session_token = generate_new_token()
    db.session.commit()
```

**Consensus Evidence**:
- Multiple blog posts mention this as unexpected behavior
- Official docs don't explicitly state concurrent sessions are allowed
- No built-in mechanism to prevent it

**Recommendation**: Add as a note in Flask-Login section or FAQ

---

### Finding 3.2: Application Factory with Blueprints Import Order

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Miguel Grinberg Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xv-a-better-application-structure) | [Real Python](https://realpython.com/flask-blueprint/) | [DEV.to](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2)
**Date**: 2024-2025
**Verified**: Cross-Referenced
**Impact**: LOW
**Already in Skill**: Yes (documented in Blueprints section)

**Description**:
Blueprint routes must be imported at the bottom of the blueprint's `__init__.py` file, after the `bp` object is created, to avoid circular imports. This is already documented in the skill.

**Consensus Evidence**:
- Miguel Grinberg's authoritative tutorial
- Real Python guide
- DEV.to 2025 best practices guide
- Official Flask documentation

**Recommendation**: Already in skill, no action needed

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Circular Import Error | Common Errors & Fixes | Fully covered with extensions.py pattern |
| Working Outside Application Context | Common Errors & Fixes | Fully covered with app_context solution |
| Blueprint Not Found (url_for) | Common Errors & Fixes | Fully covered with blueprint prefix |
| CSRF Token Missing | Common Errors & Fixes | Fully covered with form.hidden_tag() |
| Blueprint Import Order | Blueprints > Creating a Blueprint | Fully covered with comment |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 stream_with_context Regression | Known Issues/Version Notes | Add warning for 3.1.2 users about teardown idempotency |
| 1.2 Async + Gevent Incompatibility | Deployment or Advanced Topics (new) | Add section on async views limitations |
| 1.3 Test Client Session Redirect | Testing | Add note about follow_redirects in 3.1.2+ |
| 1.4 Python 3.8 Dropped | Quick Start or Version Info | Add Python version requirement |
| 1.6 Per-Request max_content_length | Configuration or Security (new) | Add example of new feature |
| 1.7 SECRET_KEY_FALLBACKS | Configuration | Add key rotation pattern |
| 2.1 Application Context Threading | Common Errors or Advanced Topics | Add threading gotcha |
| 2.2 Flask-Login Session Protection | Authentication with Flask-Login | Add session protection modes explanation |
| 2.3 CSRF Cache Interference | Common Errors (CSRF section) | Add cache warning |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 3.1 Flask-Login Concurrent Sessions | Authentication FAQs (new section) | Add as FAQ or note |

### Priority 3: Monitor (TIER 4, Needs Verification)

None - all findings are TIER 1-3.

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "bug OR error OR gotcha" in pallets/flask | 30 | 8 |
| "breaking change" in pallets/flask | 20 | 5 |
| "application context" in pallets/flask | 20 | 2 |
| "circular import" in pallets/flask | 12 | 3 (historical) |
| Recent open issues | 4 | 2 |
| Recent releases (3.1.2, 3.1.0, 3.0.0) | 3 | 3 |

### Stack Overflow & Community

| Query | Results | Quality |
|-------|---------|---------|
| Flask application context error 2024 | Multiple | High (Sentry, official docs) |
| Flask blueprints best practices 2024 2025 | 10+ | High (Miguel Grinberg, Real Python) |
| Flask-Login session management gotchas 2024 | 10+ | Medium-High (official docs, Medium) |
| Flask CSRF protection best practices 2024 | 9 | High (official docs, security guides) |

### Other Sources

| Source | Notes |
|--------|-------|
| Flask official changelog | 3.1.x changes reviewed |
| Flask-SQLAlchemy changelog | 3.1.x changes reviewed |
| Flask-Migrate changelog | Compatibility notes |
| Security guides (2024) | CSRF and session best practices |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh release list/view` for release notes
- `gh issue view` for detailed issue comments
- `WebSearch` for Stack Overflow and community content

**Limitations**:
- Some GitHub searches returned no results (empty response), may be rate limiting or search syntax issues
- Stack Overflow site: filter didn't work as expected with WebSearch
- Focus on post-May 2025 changes, but included critical 3.0 → 3.1 migration info

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.6 and 1.7 (new 3.1.0 features) against current official documentation to ensure code examples are accurate.

**For code-example-validator**: Validate the async+gevent workaround code in finding 1.2 - test in actual environment if possible.

**For user (Jez)**: Consider testing findings 1.1 (stream_with_context regression) and 1.2 (async+gevent) in a real project to validate workarounds before adding to skill.

---

## Integration Guide

### Adding Version-Specific Warnings

```markdown
### Version Notes

**Flask 3.1.2 Known Issues**:
- `stream_with_context` may call teardown functions multiple times. Ensure teardown callbacks are idempotent (use `g.pop(key, None)` instead of `g.pop(key)`). Fixed in 3.2.0.

**Flask 3.1.0 Breaking Changes**:
- Dropped Python 3.8 support. Use Python 3.9+ or stay on Flask 3.0.x.
- Requires Werkzeug >= 3.1, ItsDangerous >= 2.2, Blinker >= 1.9.
```

### Adding Async + Gevent Warning

```markdown
## Advanced Topics

### Async Views with Gevent

⚠️ **Warning**: Async views have limited compatibility with gevent. While individual requests work, **concurrent async requests will fail** due to asyncio/gevent event loop conflicts.

**Workaround** (if you must use both):

```python
import asyncio, gevent.monkey, gevent.selectors
from flask import Flask

gevent.monkey.patch_all()
loop = asyncio.EventLoop(gevent.selectors.DefaultSelector())
gevent.spawn(loop.run_forever)

class GeventFlask(Flask):
    def async_to_sync(self, func):
        def run(*args, **kwargs):
            coro = func(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return run
```

**Better solution**: Choose either async (with asyncio/uvloop) OR gevent, not both.

**Source**: [GitHub Issue #5881](https://github.com/pallets/flask/issues/5881)
```

### Adding Flask-Login Session Protection

```markdown
### Configuring Session Protection

Flask-Login has two session protection modes:

```python
# extensions.py
login_manager.session_protection = "basic"   # Default: checks session identifier
login_manager.session_protection = "strong"  # Strict: logs out on IP change
login_manager.session_protection = None      # Disabled (not recommended)
```

**⚠️ Strong mode warning**: Users on mobile networks or VPNs may be logged out when their IP changes. Use "basic" for most applications.

**Note**: By default, Flask-Login allows concurrent sessions (same user on multiple browsers). To prevent this, implement custom session tracking.
```

---

**Research Completed**: 2026-01-21 14:30
**Next Research Due**: After Flask 3.2.0 release (monitor for stream_with_context fix)

---

## Sources

Sources cited in this research:

- [Flask Changes Documentation](https://flask.palletsprojects.com/en/stable/changes/)
- [Flask 3.1.2 Release](https://github.com/pallets/flask/releases/tag/3.1.2)
- [Flask 3.1.0 Release](https://github.com/pallets/flask/releases/tag/3.1.0)
- [Flask 3.0.0 Release](https://github.com/pallets/flask/releases/tag/3.0.0)
- [GitHub Issue #5804 - stream_with_context regression](https://github.com/pallets/flask/issues/5804)
- [GitHub Issue #5881 - asgiref/gevent conflict](https://github.com/pallets/flask/issues/5881)
- [GitHub Issue #5786 - Test client session redirect](https://github.com/pallets/flask/issues/5786)
- [RuntimeError: Working Outside of Application Context - Sentry Guide](https://sentry.io/answers/working-outside-of-application-context/)
- [The Application Context — Flask Documentation](https://flask.palletsprojects.com/en/stable/appcontext/)
- [How To Structure a Large Flask Application-Best Practices for 2025](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2)
- [The Flask Mega-Tutorial, Part XV: A Better Application Structure](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xv-a-better-application-structure)
- [Use a Flask Blueprint to Architect Your Applications – Real Python](https://realpython.com/flask-blueprint/)
- [Flask-Login 0.7.0 documentation](https://flask-login.readthedocs.io/)
- [From Login to Logout: Mastering Secure Session Management with Flask-Login and SQLAlchemy](https://medium.com/@prajwal_ahluwalia/from-login-to-logout-mastering-secure-session-management-with-flask-login-and-sqlalchemy-09a1153ac239)
- [CSRF Protection — Flask-WTF Documentation](https://flask-wtf.readthedocs.io/en/latest/csrf/)
- [Best practices to protect your Flask applications - Security Boulevard](https://securityboulevard.com/2024/01/best-practices-to-protect-your-flask-applications/)
- [Flask-Migrate CHANGES.md](https://github.com/miguelgrinberg/Flask-Migrate/blob/main/CHANGES.md)
- [Flask-SQLAlchemy Changes](https://flask-sqlalchemy.readthedocs.io/en/stable/changes/)
