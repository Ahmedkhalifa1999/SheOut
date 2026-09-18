# SheOut Fix Plan

Companion to [`REVIEW.md`](REVIEW.md). Finding IDs (F, S, D) refer to that
document. The plan is split into phases that each leave the application
runnable, so they can be merged one at a time. Sizes are relative: **S** under
half a day, **M** one to two days, **L** more than two days for one developer
familiar with Django.

Suggested branch naming: `fix/phase-0-hygiene`, `fix/phase-1-models`, and so on,
each merged through a pull request that runs the checks from Phase 5 once
they exist.

## Phase 0: Repository hygiene and settings (S1, S2, S3, S4) — size S

Do this first; it is a prerequisite for everyone working on later phases.

1. **Stop tracking generated and secret files.**
   - `git rm --cached db.sqlite3` and every `__pycache__` directory.
   - Add `.gitignore` with at least: `__pycache__/`, `*.pyc`, `db.sqlite3`,
     `.env`, `/staticfiles/`, `/media/`, `.venv/`.
   - Treat the superuser password and secret key as leaked: rotate
     `SECRET_KEY`, and reset the admin password on any real deployment.
2. **Delete the duplicate theme.** Remove `SheOut Front End/` entirely; the
   live copies are `store/static/` and `store/templates/`. Keep the two use-case
   `.docx` files in a top-level `docs/` folder rather than under `static/`.
3. **Pin dependencies.** Add `requirements.txt` with a supported Django LTS
   (`Django>=4.2,<4.3` is the smallest jump; 5.2 LTS if Python 3.10+ is
   guaranteed) and `python-dotenv` or `django-environ`. Add a
   `requirements-dev.txt` with `ruff` and `pytest-django` (or use the
   built-in test runner).
4. **Move settings to the environment.** In `SheOut/settings.py` read
   `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` (optional) and
   `TIME_ZONE` from environment variables with safe defaults for development
   only. Set `TIME_ZONE = "Africa/Cairo"`. Add the `SECURE_*` and
   `*_COOKIE_SECURE` settings guarded by `not DEBUG`.
5. **Write `README.md`** with setup: create venv, install requirements,
   `migrate`, `createsuperuser`, `runserver`, and how to add a product with an
   image.
6. **Remove dead code**: unused imports listed in Appendix C, the star import in
   `store/admin.py`, the `print()` calls in `store/views.py`.

Acceptance:

- `git ls-files | grep -E '\.pyc$|db\.sqlite3'` prints nothing.
- A fresh clone follows the README to a running site with an empty database.
- `python manage.py check --deploy` with `DEBUG=0` reports no warnings other
  than HSTS/SSL ones that depend on the hosting environment.

## Phase 1: Data model (D1, D2, F5, F12) — size M

Goal: one user table, a stable product key, fields the templates actually need.

1. **Rename models to PascalCase** (`Item`, `CartItem`, `OrderLine`, `Order`)
   and add `__str__` to each. Django will generate rename migrations; verify
   with `makemigrations --check` that no table is dropped.
2. **Drop `customer`.** Replace `CartItem.customer` and `Order.customer` with
   `ForeignKey(settings.AUTH_USER_MODEL)`. Write a data migration that maps
   existing `customer.email` values to `auth_user.username` (they are equal for
   site-registered users) before removing the table.
3. **Give `Item` a surrogate key.** Add the default `BigAutoField` id, a
   `slug = SlugField(unique=True)` for URLs, keep `name` as a plain
   `CharField(max_length=100)`, change `price` to
   `DecimalField(max_digits=10, decimal_places=2)`, add
   `image = ImageField(upload_to="products/", blank=True)` (requires
   `Pillow` and `MEDIA_ROOT`/`MEDIA_URL`), add
   `stock = PositiveIntegerField(default=0)`, and make `category` non-null with
   a default. Data migration: copy `name` to `slug` via `slugify`, and set
   `image` for `blue_shirt` from the existing PNG.
4. **Constraints and validators.** `CartItem`: `MinValueValidator(1)` on
   quantity, `UniqueConstraint(user, item, size)` so re-adding merges instead
   of duplicating (F1 shows two rows for one product). `OrderLine`: quantity
   `>= 1`, price copied from item at order time (already the case, keep it).
   `Order`: `created_at = DateTimeField(auto_now_add=True)` replacing `time`,
   `address` as `TextField`, and a `status` choice field (`pending`, `paid`,
   `shipped`, `cancelled`).
5. **Model methods.** `CartItem.line_total`, `Order.total` (sum of lines),
   `Order.place_from_cart(user, address)` inside `transaction.atomic()` that
   creates lines, decrements stock (or raises if insufficient) and clears the
   cart.
6. **Admin.** Register the renamed models with `list_display` for price,
   category and stock; an inline for order lines.

Acceptance:

- `makemigrations --check` clean; `migrate` succeeds on the old committed
  database (test against a copy) and on an empty one.
- `Order.objects.create(...)` no longer emits the naive-datetime warning.
- A superuser created with `createsuperuser` can add to cart and check out.

## Phase 2: Views, forms and auth (D4, F3, F6, F7, F9) — size M

Goal: no request path can raise an unhandled exception from user input.

1. **Forms** in `store/forms.py`:
   - `RegisterForm(UserCreationForm)` using email as username and running the
     configured password validators;
   - `LoginForm = AuthenticationForm`;
   - `AddToCartForm` with `size` (choices from the model) and `quantity`
     (`IntegerField(min_value=1, max_value=20)`);
   - `CheckoutForm(ModelForm)` for `Order.address`;
   - `ShopFilterForm` with optional `q`, `category`, `min_price`, `max_price`.
2. **Split login and register** into two views (or one view with two bound
   forms) and delete the `which` hidden field. Use `django.contrib.auth.views`
   `LoginView`/`LogoutView` where possible. Add `LOGIN_URL`,
   `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` to settings.
3. **Decorate** every storefront view with `@login_required` and remove the
   hand-written checks. Decide whether browsing should require login at all;
   most stores let anonymous users view the shop and only gate the cart.
4. **Replace lookups**: `filter(...)[0]` becomes `get_object_or_404`;
   `request.POST['x']` becomes `form.cleaned_data['x']`; all writes go through
   `transaction.atomic()`.
5. **Delete** `store/inventory_management/` and `store/customer_management/`.
   Whatever logic survives moves to model methods (Phase 1 step 5) or a single
   `store/services.py`.
6. **Cart views**: `cart_add` (POST), `cart_update` (POST, quantity per line),
   `cart_remove` (POST), `cart` (GET). Use URL names and `{% url %}` in
   templates instead of hard-coded paths.
7. **Messages.** Use `django.contrib.messages` for "added to cart", "invalid
   credentials", "email already registered", "order placed", and render them
   in the base template.
8. **404 and 500 templates** so that production errors are not blank pages.

Acceptance:

- Every request in REVIEW.md Appendix A returns 200, 302 or 4xx; none returns
  500. Re-run `docs/review/reproduce_flows.py` after updating its URLs.
- Registering with an existing email shows an error and creates nothing.
- Checking out an empty cart is refused with a message.

## Phase 3: Templates and static assets (D5, F1, F2, F4, F8, F10, F11) — size M

1. **Base template.** Create `store/templates/base.html` with the `<head>`,
   navbar (as an include), messages block, footer, and a `{% block content %}`.
   Convert the seven pages to `{% extends "base.html" %}` and delete their
   duplicated chrome. Target: each page template under 100 lines.
2. **Static fixes.** Replace `{% static 'https://...' %}` with plain
   `<link href="https://...">`; rename `Capture2.JPG` to a lowercase filename
   and reference it once in the navbar include; make footer images
   `{% static %}` paths; add the theme's `js/` bundle (jQuery, Bootstrap,
   owl-carousel, etc.) or remove the components that depend on it; add
   `nice-select.css` or drop its import.
3. **Quote every attribute** that contains a template variable
   (`value="{{ ... }}"`, `src="{{ ... }}"`, `href="{% url ... %}"`).
4. **Cart page.** Remove the Lorem ipsum row. Render one row per `CartItem`
   with image, name, size, unit price, a quantity form, line total, and a
   POST remove button. Show the cart total and disable Checkout when empty.
   Remove the `alert()` handlers.
5. **Shop page.** Bind the sidebar to `ShopFilterForm` (GET). Category links
   become `?category=Shirts`. Show "no results" and a reset link. Paginate at
   12 items.
6. **Checkout page.** Render the real lines and total from the cart; delete the
   hard-coded `$ 388` block and the unsubmitted payment/shipping radios, or
   move them inside the form and store them on the order.
7. **Item page.** Use `item.image.url` with a placeholder fallback; show stock
   status; URL becomes `/item/<slug>/`.
8. **Order confirmation and history** pages (`/orders/`, `/orders/<id>/`) so a
   customer can see what they bought.

Acceptance:

- Headless browser walk (`docs/review/browser_walk.js`) reports zero failed
  requests on every page.
- Cart screenshot shows correct price, quantity, size and total for a real
  item and no placeholder row.
- Shop filters change the result set.

## Phase 4: Tests and CI (S5) — size M

1. **Test suite** in `store/tests/`:
   - `test_models.py`: `Order.total`, `place_from_cart` atomicity and stock
     decrement, cart merge on duplicate add.
   - `test_auth.py`: register (valid, duplicate email, weak password), login
     (wrong password shows message), logout, `login_required` redirects.
   - `test_cart.py`: add/update/remove, invalid quantity rejected, unknown item
     404, name with spaces works.
   - `test_checkout.py`: empty cart refused, order created with lines, cart
     cleared, address length enforced.
   - `test_shop.py`: search, category and price filters, pagination.
   - `test_templates.py`: every page renders with no missing static file
     (assert on `{% static %}` output or use `collectstatic --dry-run`).
   Each finding in REVIEW.md section 3 should map to at least one test.
2. **Lint and format.** `ruff` configuration in `pyproject.toml`; fix the
   findings in Appendix C.
3. **GitHub Actions** workflow on push and pull request: install requirements,
   `ruff check`, `python manage.py check`, `makemigrations --check`,
   `python manage.py test`, and `python manage.py collectstatic --noinput`.
4. **Branch protection** on `main` requiring the workflow to pass.

Acceptance: CI green on the default branch; coverage of `store/views.py` and
`store/models.py` above 80 percent.

## Phase 5: Product completeness (D6) — size L, optional

Items that turn the prototype into a usable store once the above is done:

- stock enforcement at add-to-cart and checkout, with an "out of stock" state;
- order status workflow in the admin and email confirmation on order placement
  (console backend in development);
- a real payment step or an explicit "cash on delivery" flow;
- user profile page with saved address;
- product search index (`icontains` on name and category is enough at this
  size);
- image thumbnails (`sorl-thumbnail` or `easy-thumbnails`) and WhiteNoise for
  static files in production;
- accessibility pass on the theme: alt text, form labels, focus states;
- decide whether anonymous browsing is allowed and whether carts should
  persist in the session for anonymous users.

## Traceability

| Finding | Phase / step |
|---|---|
| F1 cart renders no price/image | 3.4 (and 1.3, 2.5) |
| F2 cart cannot be edited | 2.6, 3.4 |
| F3 500s from user input | 2.1, 2.4, 2.8 |
| F4 unquoted attributes | 3.3 |
| F5 accounts without customer row | 1.2 |
| F6 registration logic | 2.1, 2.2, 2.7 |
| F7 no validation | 1.4, 2.1 |
| F8 filters dead | 2.1, 3.5 |
| F9 login feedback / logout | 2.2, 2.7 |
| F10 broken static references | 3.2 |
| F11 no JavaScript | 3.2 |
| F12 naive datetimes | 0.4, 1.4 |
| S1 database committed | 0.1 |
| S2 dev settings in deployment | 0.4 |
| S3 no manifest, EOL Django | 0.3 |
| S4 bytecode and duplicate theme | 0.1, 0.2 |
| S5 no tests, debug output | 0.6, 4.1, 4.2, 4.3 |
| D1 name as primary key | 1.3 |
| D2 two user tables | 1.2 |
| D3 wrapper classes | 2.5 |
| D4 no forms / login_required | 2.1, 2.3 |
| D5 no base template | 3.1 |
| D6 thin domain model | 1.4, 1.5, 3.6, 3.8, 5 |
