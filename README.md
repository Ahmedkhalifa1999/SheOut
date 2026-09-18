# SheOut

A small Django storefront: browse products by category, search and filter,
add items to a cart, check out with a delivery address, and review past orders.
Staff manage products, stock and orders through the Django admin.

## Requirements

- Python 3.10 or newer
- pip

## Local setup

```bash
git clone https://github.com/Ahmedkhalifa1999/SheOut.git
cd SheOut
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # DJANGO_DEBUG=1 is already set for development
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The admin is at <http://127.0.0.1:8000/admin/>.

### Adding products

1. Log in to the admin as the superuser.
2. Under **Store → Products → Add**, fill in name, category, price and **stock**
   (products with zero stock show as sold out and cannot be added to a cart).
3. Upload an image if you have one. `docs/sample-data/blue_shirt.png` is a
   sample. Products without an image show a placeholder.

## Configuration

All settings that differ between machines come from environment variables,
or from a `.env` file in the project root. `.env.example` lists them:

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG` | `1` for development. Off by default. |
| `DJANGO_SECRET_KEY` | Required when debug is off. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins for form posts behind a proxy. |
| `DJANGO_SQLITE_PATH`, `DJANGO_MEDIA_ROOT` | Where the database and uploaded images live. |
| `DJANGO_TIME_ZONE` | Defaults to `Africa/Cairo`. |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS` | HTTPS hardening when debug is off. |

With debug off, Django also sets secure cookies and the other headers that
`manage.py check --deploy` asks for. Uploaded product images are stored under
`MEDIA_ROOT` and served by Django only in debug mode; put a web server in front
of `media/` and `staticfiles/` (`python manage.py collectstatic`) in production.

## Development checks

```bash
ruff check . && ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs the same checks
on every push and pull request.

## Project layout

```
SheOut/            project settings and root URL configuration
store/             the shop app: models, forms, views, urls, admin, templates, static
store/tests/       test suite, one module per area (models, auth, cart, checkout, shop, templates, migrations)
docs/review/       the code review that motivated the current structure, with reproduction scripts
docs/use-cases/    original use-case write-ups
REVIEW.md          findings from the review
FIX_PLAN.md        the plan the current code follows
```
