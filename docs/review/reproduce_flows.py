"""Scripted HTTP walk used for REVIEW.md Appendix A.

Usage (from the repository root, with the dev server running):

    python manage.py runserver 127.0.0.1:8000
    python manage.py shell < docs/review/seed_fixtures.py
    python docs/review/reproduce_flows.py [http://127.0.0.1:8000]

Only the standard library is used. Each line prints the request, the status
code, any redirect target, and for 500 responses the exception shown on the
Django debug page. A trailing "<-- expected N" marks a result that differs from
what the review recorded, which is how to check progress on FIX_PLAN.md.

Warning: this writes to the configured database (users, cart rows, orders).
Run it against a scratch copy, never against production data.
"""
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect
        )

    def request(self, method, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(BASE + path, data=body, method=method)
        try:
            resp = self.opener.open(req)
            return resp.getcode(), resp.headers.get("Location"), resp.read().decode(errors="replace")
        except urllib.error.HTTPError as err:
            return err.code, err.headers.get("Location"), err.read().decode(errors="replace")

    def csrf(self, path):
        _, _, html = self.request("GET", path)
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        return match.group(1) if match else None

    def post(self, path, data, csrf_from=None):
        payload = dict(data)
        payload["csrfmiddlewaretoken"] = self.csrf(csrf_from or path)
        return self.request("POST", path, payload)


def exception_summary(html):
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    value = re.search(r'<pre class="exception_value">(.*?)</pre>', html, re.S)
    text = re.sub(r"\s+", " ", title.group(1)).strip()[:80] if title else ""
    if value:
        text += " :: " + re.sub(r"\s+", " ", value.group(1))[:120]
    return text


def show(label, result, expect=None):
    code, location, html = result
    line = f"{label:70s} {code}"
    if location:
        line += " -> " + location
    if code >= 500:
        line += "  [" + exception_summary(html) + "]"
    if expect is not None and code != expect:
        line += f"   <-- expected {expect}"
    print(line)
    return html


def names_in_cart(html):
    return re.findall(r'<td class="name-pr">\s*<a href="#">\s*(.*?)\s*</a>', html, re.S)


print("########## HAPPY PATH ##########")
c = Client()
show("GET /  (anonymous)", c.request("GET", "/"), 302)
show("GET /shop/ (anonymous)", c.request("GET", "/shop/"), 302)
show("GET /login_register/", c.request("GET", "/login_register/"), 200)
show("POST register reviewer@test.com / pw 'x' (1 char, no validators?)",
     c.post("/login_register/", {"which": "register", "email": "reviewer@test.com", "password": "x"}), 302)
show("GET / (logged in)", c.request("GET", "/"), 200)
html = show("GET /shop/", c.request("GET", "/shop/"), 200)
print("   items listed:", re.findall(r"<h4>(.*?)</h4>", html)[:-1])
html = show("GET /item/?name=blue_shirt", c.request("GET", "/item/?name=blue_shirt"), 200)
hidden = re.search(r'<input type="hidden" name="item_name"[^>]*>', html)
print("   hidden input:", hidden.group(0) if hidden else None)
show("POST /item/ add blue_shirt size M qty 2",
     c.post("/item/", {"item_name": "blue_shirt", "size": "M", "quantity": "2"}, csrf_from="/item/?name=blue_shirt"), 302)
show("POST /item/ add blue_shirt again size L qty 1 (duplicate row?)",
     c.post("/item/", {"item_name": "blue_shirt", "size": "L", "quantity": "1"}, csrf_from="/item/?name=blue_shirt"), 302)
html = show("GET /cart/", c.request("GET", "/cart/"), 200)
print("   cart rows rendered:", names_in_cart(html))
print("   price cells:", re.findall(r'<td class="price-pr">\s*<p>(.*?)</p>', html, re.S))
print("   img srcs in cart:", re.findall(r'<img class="img-fluid" src=([^ >]*)', html)[:4])
print("   qty inputs:", re.findall(r'type="number" size="4" value="(\d+)"', html))
show("GET /checkout/", c.request("GET", "/checkout/"), 200)
show("POST /checkout/ address='any place'", c.post("/checkout/", {"address": "any place"}), 302)
html = show("GET /cart/ after checkout (should be empty)", c.request("GET", "/cart/"), 200)
print("   cart rows rendered:", names_in_cart(html))

print("\n########## EDGE CASES ##########")
show("GET /item/ (no ?name)", c.request("GET", "/item/"), 500)
show("GET /item/?name=nope", c.request("GET", "/item/?name=nope"), 302)
html = show("GET /item/?name=red shirt (name with a space)", c.request("GET", "/item/?name=red%20shirt"), 200)
hidden = re.search(r'<input type="hidden" name="item_name"[^>]*>', html)
print("   hidden input rendered as:", hidden.group(0) if hidden else None)
show("POST /item/ item_name='red' (what the browser sends)",
     c.post("/item/", {"item_name": "red", "size": "M", "quantity": "1"}, csrf_from="/item/?name=blue_shirt"), 500)
show("POST /item/ quantity=abc",
     c.post("/item/", {"item_name": "blue_shirt", "size": "M", "quantity": "abc"}, csrf_from="/item/?name=blue_shirt"), 500)
show("POST /item/ quantity=-3",
     c.post("/item/", {"item_name": "blue_shirt", "size": "M", "quantity": "-3"}, csrf_from="/item/?name=blue_shirt"), 500)
show("POST /item/ quantity=0 size=GIANT (accepted?)",
     c.post("/item/", {"item_name": "blue_shirt", "size": "GIANT", "quantity": "0"}, csrf_from="/item/?name=blue_shirt"), 302)
show("POST /item/ missing size field",
     c.post("/item/", {"item_name": "blue_shirt", "quantity": "1"}, csrf_from="/item/?name=blue_shirt"), 500)
show("POST /checkout/ with address of 300 chars (max_length=50)", c.post("/checkout/", {"address": "A" * 300}), 302)
show("POST /checkout/ with EMPTY cart (creates empty order?)", c.post("/checkout/", {"address": "nowhere"}), 302)
show("GET /shop/?q=zzz&minprice=900 (filters ignored?)", c.request("GET", "/shop/?q=zzz&minprice=900&maxprice=1000"), 200)
show("GET /logout/", c.request("GET", "/logout/"), 404)
show("GET /static/images/LOGO/Capture2.jpg (lowercase ext as in template)", c.request("GET", "/static/images/LOGO/Capture2.jpg"), 404)
show("GET /static/images/LOGO/Capture2.JPG (actual file)", c.request("GET", "/static/images/LOGO/Capture2.JPG"), 200)
show("GET /static/product_images/red shirt.png", c.request("GET", "/static/product_images/red%20shirt.png"), 404)

print("\n########## AUTH EDGE CASES ##########")
c2 = Client()
show("POST login wrong password (any error shown?)",
     c2.post("/login_register/", {"which": "login", "email": "reviewer@test.com", "password": "wrong"}), 302)
show("POST login missing 'which' field",
     c2.post("/login_register/", {"email": "reviewer@test.com", "password": "x"}), 500)
show("POST register EXISTING email w/ wrong pw (silently fails?)",
     c2.post("/login_register/", {"which": "register", "email": "reviewer@test.com", "password": "different"}), 302)
show("POST register email='ahmed' (auth username exists, no customer row)",
     c2.post("/login_register/", {"which": "register", "email": "ahmed", "password": "pw"}), 500)
show("POST register email='not-an-email' (server-side validation?)",
     c2.post("/login_register/", {"which": "register", "email": "not-an-email", "password": "pw"}), 302)
c3 = Client()
show("POST login as staff@shop.com (auth user, no customer row)",
     c3.post("/login_register/", {"which": "login", "email": "staff@shop.com", "password": "staffpass123"}), 302)
show("POST /item/ add to cart as that user",
     c3.post("/item/", {"item_name": "blue_shirt", "size": "M", "quantity": "1"}, csrf_from="/item/?name=blue_shirt"), 500)
show("POST /checkout/ as that user", c3.post("/checkout/", {"address": "x"}), 500)
