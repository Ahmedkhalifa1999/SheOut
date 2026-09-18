# SheOut Code Review

| | |
|---|---|
| Reviewed commit | `e2e4122` (`main`, "final push", 2022-05-17) |
| Review date | 2026-09-18 |
| Stack | Django 4.0.3 on Python 3.11 (project bytecode was compiled with CPython 3.9) |
| Companion documents | [`FIX_PLAN.md`](FIX_PLAN.md), evidence and scripts in [`docs/review/`](docs/review/) |

## 1. Summary

SheOut is a Django storefront with a copied HTML theme: register or log in, browse
items, view one item, add it to a cart, check out with an address. It builds and
runs, and the happy path completes if the user types carefully. It is not a
working store:

- the cart page shows no prices or images and cannot be edited;
- search, category and price filters do nothing;
- nine ordinary user actions return HTTP 500 pages with full tracebacks;
- accounts created through the Django admin cannot buy anything;
- the repository ships its SQLite database, including the superuser's password
  hash and two session keys, plus compiled bytecode and two copies of the theme.

The code has a reasonable shape for a student project (an app, models,
migrations, CSRF tokens on every form, hashed passwords) but every layer between
the browser and the database is either missing (forms, validation, base
template, tests, logout) or actively loses data (the wrapper classes in
`store/inventory_management` and `store/customer_management`).

Findings are numbered so the fix plan can reference them: **F** = functional
bug reproduced on a running server, **S** = security or repository hygiene,
**D** = design and code quality.

## 2. How the review was run

```
pip install django==4.0.3
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py showmigrations store
python manage.py test
python -m pyflakes SheOut store
python manage.py runserver 127.0.0.1:8000
python manage.py shell < docs/review/seed_fixtures.py
python docs/review/reproduce_flows.py          # scripted HTTP walk, Appendix A
node docs/review/browser_walk.js               # headless Chromium, Appendix B
```

| Check | Result |
|---|---|
| `manage.py check` | passes, 0 issues |
| `manage.py check --deploy` | 7 warnings (Appendix D) |
| `makemigrations --check` | no drift between models and migrations |
| `showmigrations` | all 4 store migrations applied in the committed DB |
| `manage.py test` | 0 tests found |
| pyflakes | 15 findings (Appendix C) |
| scripted HTTP walk | 9 of 37 requests returned HTTP 500 |
| headless browser walk | 17 failed asset requests, no JavaScript loaded |

The committed `db.sqlite3` was backed up before the run and restored afterwards.

## 3. Functional bugs (all reproduced)

### F1. The cart page renders no price, no image, and a fake row

`store/customer_management/product.py:30` builds cart entries from a
`cart_item` helper class whose constructor sets only `name`, `size` and
`quantity`. `store/templates/cart.html:178` and `:187` read `item.image` and
`item.price`, which do not exist, so both render as empty strings. The quantity
box at `cart.html:189` is hard-coded to `1` and the total cell to `$ 80.0`. A
hard-coded "Lorem ipsum dolor sit amet" row at `cart.html:150-172` is rendered
above the real rows for every customer. Screenshot: `docs/review/cart-page.png`.

### F2. The cart cannot be edited

The "X" remove buttons (`cart.html:170`, `:195`) and "Update Cart"
(`cart.html:219`) are `<form>`s with no fields that GET `/cart` or `/shop`.
There is no remove, update, or clear view. The only way to empty a cart is to
place an order. The "Checkout" button at `cart.html:209` fires an
`alert('Order confirmed')` before any order exists.

### F3. Ordinary input crashes the server

Every view reads `request.POST[...]` / `request.GET[...]` directly with no form
class. Reproduced 500s:

| Request | Exception | Where |
|---|---|---|
| `GET /item/` (no `name`) | `MultiValueDictKeyError: 'name'` | `store/views.py:33` |
| `POST /item/` without `size` | `MultiValueDictKeyError: 'size'` | `store/views.py:30` |
| `POST /item/` `quantity=abc` | `ValueError: Field 'quantity' expected a number` | `product.py:23` |
| `POST /item/` `quantity=-3` | `IntegrityError: CHECK constraint failed: quantity` | `product.py:23` |
| `POST /item/` unknown `item_name` | `IndexError: list index out of range` | `product.py:22` |
| `POST /login_register/` without `which` | `MultiValueDictKeyError: 'which'` | `store/views.py:68` |

Because `DEBUG = True`, each of these returns Django's debug page with the full
traceback and settings dump.

### F4. Item names containing a space cannot be added to the cart

`store/templates/shop-detail.html:199` renders
`<input type="hidden" name="item_name" value={{ name }}>` without quotes. For an
item named `red shirt` the browser submits `item_name=red`, which reaches the
`IndexError` in F3. The same unquoted pattern appears at `cart.html:178`
(`src={{item.image}}`), which made the browser request `/cart/alt=""`.

### F5. Any account without a `store.customer` row crashes add-to-cart and checkout

Users are stored twice: in `auth_user` (created by
`store/customer_management/customer.py:19`) and in `store_customer` (an email
primary key, `store/models.py:27`). Only the site's register form creates both.
The committed superuser `ahmed` and any user created in the admin have no
customer row, so `product.py:21` and `orders.py:14` raise `IndexError` on
`filter(...)[0]`. Reproduced with a user created via `create_user` only.

### F6. Registration logic is inverted, ignored, and non-atomic

- `customer.py:14` `register_user` returns `exists`, i.e. `True` when
  registration did **not** happen. The docstring above it says the opposite.
- `store/views.py:69` ignores the return value and immediately calls
  `authenticate_user`. Re-registering an existing email with a different
  password therefore "succeeds" with a redirect to `/`, which redirects back to
  the login page. No message is shown.
- If the email exists in `auth_user` but not in `store_customer` (for example
  `ahmed`), the customer row is inserted, then `create_user` raises
  `IntegrityError: UNIQUE constraint failed: auth_user.username`. Nothing is in a
  transaction, so the orphan customer row stays. Reproduced.

### F7. No validation anywhere

Reproduced on the running server:

- password `x` (one character) accepted: `AUTH_PASSWORD_VALIDATORS` are
  configured but never invoked because registration bypasses Django forms;
- email `not-an-email` accepted, creating both a user and a customer;
- `size=GIANT` and `quantity=0` stored in the cart and copied into an order line;
- a 300-character address stored against `max_length=50` (SQLite does not
  enforce `VARCHAR` lengths, and no `full_clean()` is called);
- checking out an empty cart creates an order with no lines. The committed
  database already contains five such orders (ids 1-5).

### F8. Search, category and price filters are dead

`store/views.py:14` constructs `shop.filter_parameters()` with its defaults and
never reads `request.GET`, so `shop.py:22` always returns every item. In
`shop.html`: the search box at `:152` has no `name` attribute so it submits
nothing; the category links at `:162-166` point to `#about`, `#services`,
`#clients`; the price inputs at `:175-177` are named but unread. The header
search box (`name="q"`) is not inside a form.

### F9. No feedback on failed login, no logout

A wrong password redirects back to `/login_register/` with no message
(`views.py:76`). There is no logout URL anywhere; `GET /logout/` is a 404. The
messages framework is installed but unused.

### F10. Broken static references on every page

Observed as failed requests in the browser walk (Appendix B):

- `index.html:93`, `:205`, `:206`, `:313`, `:314` wrap absolute CDN URLs in
  `{% static %}`, producing `/static/https%3A/cdnjs.cloudflare.com/...`;
- `index.html:58` and `about.html:46` reference `images/LOGO/Capture2.jpg`; the
  file is `Capture2.JPG`, so the logo is missing on Linux;
- `shop.html:233` onward uses relative `images/instagram-*.jpg`, which resolve
  under `/shop/`;
- product images are located by convention as
  `static/product_images/<name>.png` (`shop.py:14`, `views.py:39`). Only
  `blue_shirt.png` exists, so every other item shows a broken image;
- `store/static/css/style.css:29` imports `nice-select.css`, which is not
  present in the repository.

### F11. No JavaScript is loaded

The templates contain no `<script>` tags other than two IE8 shims
(`shop.html:35-36`, `checkout.html:35-36`). The theme's `js/` directory was
never added to `store/static`. Neither jQuery nor Bootstrap JS loads, so the
navbar dropdowns, the product carousel, the mobile menu toggle and the
"quantity" widgets are inert.

### F12. Naive datetimes

`store/inventory_management/orders.py:15` stamps orders with
`datetime.datetime.now()` while `USE_TZ = True`. Django emits
`RuntimeWarning: DateTimeField order.time received a naive datetime` on every
checkout. `TIME_ZONE = 'EET'` is an ambiguous abbreviation; use
`Africa/Cairo`.

## 4. Security and repository hygiene

### S1. The SQLite database is committed

`db.sqlite3` (188 KB) is tracked. It contains the superuser `ahmed` with a
`pbkdf2_sha256` password hash, a customer account hash, two session keys, and
test orders. Deleting the file does not remove it from history; the password
must be considered public and the secret key rotated so those sessions cannot be
replayed.

### S2. Development settings are the deployment settings

`SheOut/settings.py:23` ships the generated `django-insecure-...` secret key,
`:26` sets `DEBUG = True`, `:28` leaves `ALLOWED_HOSTS` empty. `check --deploy`
lists seven warnings (Appendix D). With DEBUG on, every crash in F3 exposes
source, locals and settings to the user.

### S3. No dependency manifest, unsupported Django

There is no `requirements.txt`, `pyproject.toml`, `README`, or `.gitignore`. The
only version hint is the docstring in `settings.py` naming Django 4.0.3. The
4.0 series reached end of life in April 2023; several security releases
(4.0.4 through 4.0.10) fixed SQL-injection and DoS issues after 4.0.3.

### S4. Compiled bytecode and duplicated assets are tracked

Twenty `*.cpython-39.pyc` files are committed, including bytecode for
`store/inventory_management/availability.py` and `checkout.py`, modules that
were deleted from the source tree. The entire HTML theme is tracked twice:
`SheOut Front End/` (5.5 MB) and `store/static/` plus `store/templates/`
(6.1 MB). The two HTML copies have diverged (81 to 571 differing lines per
page), so the "Front End" directory is dead weight that will mislead
contributors.

### S5. No tests, leftover debug output, unused imports

`store/tests.py` is the empty stub. `store/views.py:16-19` prints every item's
name, price and image path to stdout on each shop request. pyflakes reports
nine unused imports, an unused `import email` shadowed by parameters, and a
star import in `store/admin.py:2` (Appendix C).

### S6. What is done right

Every POST form includes `{% csrf_token %}`; passwords go through
`User.objects.create_user` and are hashed; templates autoescape; `on_delete`
is set thoughtfully (`RESTRICT` on items referenced by orders). No injection
path from customer-controlled input was found. The unquoted attributes in F4
are an attribute-injection risk only for values set by admins.

## 5. Design and code quality

### D1. Product name is the primary key

`store/models.py:22` uses `name` (`max_length=20`) as the primary key. The name
also serves as the URL parameter (`/item/?name=`), the image filename, the cart
reference and the order-line reference. Products cannot be renamed, names are
limited to 20 characters, and spaces or punctuation break the flow (F4).

### D2. Two user tables

`store.customer` duplicates the email already stored on `auth.User` and is the
root cause of F5 and F6. A `OneToOneField` profile, or simply foreign keys to
`settings.AUTH_USER_MODEL`, removes the second table and the `filter(...)[0]`
lookups.

### D3. Wrapper classes that lose data

`inventory_management/shop.py`, `inventory_management/orders.py` and
`customer_management/product.py` copy ORM rows into ad-hoc classes
(`item`, `order_item`, `cart_item`) with a subset of fields. This is the direct
cause of F1 and adds three files of indirection over what a queryset passed to
the template would do. The module names promise inventory and customer
management but there is no stock tracking and no customer management beyond
one insert.

### D4. No Django forms, no `login_required`

Seven views repeat the same three-line authentication check by hand
(`views.py:7`, `:12`, `:27`, `:44`, `:53`, `:62`). None uses a `Form` or
`ModelForm`, which is why F3 and F7 exist. `get_object_or_404` is never used.

### D5. No base template

Each of the seven templates is a complete 126 to 376 line copy of the theme
page, 1,773 lines in total. They have already drifted: the logo path is
`logo.png` on some pages and `Capture2.jpg`/`Capture2.JPG` on others, and the
top bar appears only on the item page.

### D6. Thin domain model and misleading UI

No stock quantity, no order total, no order status, no order confirmation or
history page. `checkout.html:161` shows a hard-coded `$ 388` grand total, and
the payment (`:88`) and shipping (`:104`) radio buttons sit outside the only
form, so they are never submitted. Prices are `PositiveIntegerField` with the
currency hard-coded in templates as both `EGP` and `$`. Model classes are
lowercase (`item`, `cart_item`, `orderling`), comments include transliterated
Arabic (`shop.py:21`, `models.py:40`), and the triple-quoted strings placed
*before* functions (`customer.py:7`, `product.py:17`) are not docstrings.

## 6. Priority order

1. S1, S2, S3, S4: get secrets and binaries out of git, pin dependencies,
   configure settings from the environment.
2. D2, D1: fix the data model (single user table, surrogate product key).
3. D4, F3, F6, F7, F9: forms, `login_required`, transactions, messages, logout.
4. D3, F1, F2, F8: delete the wrappers, pass model instances to templates,
   working cart, working filters.
5. D5, F10, F11, F4: base template, static paths, theme JavaScript, quoted
   attributes.
6. S5: tests for every finding above, CI.
7. D6, F12: totals, stock, order history, timezone-aware timestamps.

The step-by-step version of this list is in [`FIX_PLAN.md`](FIX_PLAN.md).

## Appendix A: scripted HTTP walk (`docs/review/reproduce_flows.py`)

```
########## HAPPY PATH ##########
GET /  (anonymous)                                                     302 -> /login_register/
GET /shop/ (anonymous)                                                 302 -> /login_register/
GET /login_register/                                                   200
POST register reviewer@test.com / pw 'x' (1 char, no validators?)      302 -> /
GET / (logged in)                                                      200
GET /shop/                                                             200
   items listed: ['blue_shirt', 'red shirt', 'black pants']
GET /item/?name=blue_shirt                                             200
   hidden input: <input type="hidden" name="item_name" value=blue_shirt>
POST /item/ add blue_shirt size M qty 2                                302 -> /shop
POST /item/ add blue_shirt again size L qty 1 (duplicate row?)         302 -> /shop
GET /cart/                                                             200
   cart rows rendered: ['Lorem ipsum dolor sit amet', 'blue_shirt', 'blue_shirt']
   price cells: ['$ 80.0', '', '']
   img srcs in cart: ['"/static/images/img-pro-01.jpg"', '', '']
   qty inputs: ['1', '1', '1']
GET /checkout/                                                         200
POST /checkout/ address='any place'                                    302 -> /
GET /cart/ after checkout (should be empty)                            200
   cart rows rendered: ['Lorem ipsum dolor sit amet']

########## EDGE CASES ##########
GET /item/ (no ?name)                                                  500  [MultiValueDictKeyError at /item/ :: 'name']
GET /item/?name=nope                                                   302 -> /shop
GET /item/?name=red shirt (name with a space)                          200
   hidden input rendered as: <input type="hidden" name="item_name" value=red shirt>
POST /item/ item_name='red' (what the browser sends)                   500  [IndexError at /item/ :: list index out of range]
POST /item/ quantity=abc                                               500  [ValueError at /item/ :: Field 'quantity' expected a number but got 'abc'.]
POST /item/ quantity=-3                                                500  [IntegrityError at /item/ :: CHECK constraint failed: quantity]
POST /item/ quantity=0 size=GIANT (accepted?)                          302 -> /shop
POST /item/ missing size field                                         500  [MultiValueDictKeyError at /item/ :: 'size']
POST /checkout/ with address of 300 chars (max_length=50)              302 -> /
POST /checkout/ with EMPTY cart (creates empty order?)                 302 -> /
GET /shop/?q=zzz&minprice=900 (filters ignored?)                       200
GET /logout/                                                           404
GET /static/images/LOGO/Capture2.jpg (lowercase ext as in template)    404
GET /static/images/LOGO/Capture2.JPG (actual file)                     200
GET /static/product_images/red shirt.png                               404

########## AUTH EDGE CASES ##########
POST login wrong password (any error shown?)                           302 -> /login_register/
POST login missing 'which' field                                       500  [MultiValueDictKeyError at /login_register/ :: 'which']
POST register EXISTING email w/ wrong pw (silently fails?)             302 -> /
POST register email='ahmed' (auth username exists, no customer row)    500  [IntegrityError at /login_register/ :: UNIQUE constraint failed: auth_user.username]
POST register email='not-an-email' (server-side validation?)           302 -> /
POST login as staff@shop.com (auth user, no customer row)              302 -> /
POST /item/ add to cart as that user                                   500  [IndexError at /item/ :: list index out of range]
POST /checkout/ as that user                                           500  [IndexError at /checkout/ :: list index out of range]
```

Database state after the walk (orders 1-6 were already in the committed file):

```
customers: ['first@shop.com', 'reviewer@test.com', 'ahmed', 'not-an-email']
orders:
  1..5 first@shop.com  addr_len=9    lines= []                     <- empty orders, pre-existing
  6    first@shop.com  addr_len=9    lines= [('blue_shirt', '4', 1, 80)]   <- size '4', pre-existing
  7    reviewer@...    addr_len=9    lines= [('blue_shirt','M',2,80), ('blue_shirt','L',1,80)]
  8    reviewer@...    addr_len=300  lines= [('blue_shirt','GIANT',0,80)]
  9    reviewer@...    addr_len=7    lines= []
```

## Appendix B: headless browser walk (`docs/review/browser_walk.js`)

```
submit buttons on /login_register/: Login and Register both have a form owner
after clicking Register: url = / | POST sent = true
jQuery loaded: false
after Add to cart landed on: /shop/
after clicking Remove X: url = /cart/ | rows still = 2
after Place Order landed on: /

failed requests / console errors:
   404 /static/css/nice-select.css
   404 /static/images/LOGO/Capture2.jpg
   404 /static/https%3A/cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css
   404 /static/https%3A/fonts.googleapis.com/icon%3Ffamily%3DMaterial%2BIcons
   404 /static/https%3A/use.fontawesome.com/releases/v5.5.0/css/all.css
   404 /shop/images/instagram-img-01.jpg  (and -02 through -09)
   404 /static/product_images/red%20shirt.png
   404 /static/product_images/black%20pants.png
   404 /cart/alt=%22%22
```

Screenshots: `docs/review/cart-page.png`, `docs/review/shop-page.png`.

## Appendix C: pyflakes

```
store/admin.py:2:1: 'from .models import *' used; unable to detect undefined names
store/admin.py:6-10: 'item', 'customer', 'order', 'orderling', 'cart_item' may be undefined, or defined from star imports
store/tests.py:1:1: 'django.test.TestCase' imported but unused
store/views.py:2:1: 'django.http.HttpResponse' imported but unused
store/views.py:3:1: '.inventory_management.orders' imported but unused
store/customer_management/product.py:2:1: '..inventory_management.orders.order_item' imported but unused
store/customer_management/product.py:3:1: 'store.models.customer' imported but unused
store/customer_management/product.py:4:1: 'datetime' imported but unused
store/customer_management/customer.py:1:1: 'email' imported but unused
store/customer_management/customer.py:14:19: redefinition of unused 'email' from line 1
store/customer_management/customer.py:29:32: redefinition of unused 'email' from line 1
```

## Appendix D: `manage.py check --deploy`

```
security.W004  SECURE_HSTS_SECONDS not set
security.W008  SECURE_SSL_REDIRECT not True
security.W009  SECRET_KEY is the auto-generated 'django-insecure-' key
security.W012  SESSION_COOKIE_SECURE not True
security.W016  CSRF_COOKIE_SECURE not True
security.W018  DEBUG is True
security.W020  ALLOWED_HOSTS is empty
```
