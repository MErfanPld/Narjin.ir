#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت تست خودکار همه‌ی اندپوینت‌های API نارژین
=================================================
این اسکریپت فایل OpenAPI/Swagger schema پروژه رو می‌خونه، همه‌ی مسیرها (paths) و
متدها (GET/POST/PUT/PATCH/DELETE) رو استخراج می‌کنه، برای هر کدوم بر اساس
اسکیمای واقعی (requestBody / examples) یه بدنه‌ی نمونه می‌سازه، در صورت نیاز
لاگین می‌کنه تا توکن JWT بگیره، همه رو صدا می‌زنه و در آخر یک گزارش کامل از
وضعیت هر اندپوینت (موفق / خطای کلاینت 4xx / خطای سرور 5xx) نشون می‌ده.

نحوه‌ی اجرا:
    pip install pyyaml requests
    python test_api.py --spec Project_API_2_.yaml --base-url http://127.0.0.1:8000 \
        --phone 09120000000 --password YourPassword123

آرگومان‌های مهم:
    --spec        مسیر فایل yaml/json اسکیمای OpenAPI (پیش‌فرض همین پوشه)
    --base-url    آدرس ریشه‌ی سروری که پروژه روش اجرا شده
    --phone       شماره تلفن یک کاربر معتبر برای لاگین خودکار (اختیاری)
    --password    پسورد همون کاربر (اختیاری)
    --token       اگر از قبل توکن JWT داری، مستقیم بده (اختیاری، جای لاگین رو می‌گیره)
    --id          مقداری که به جای پارامترهای مسیر مثل {id} گذاشته میشه (پیش‌فرض 1)
    --timeout     تایم‌اوت هر ریکوئست به ثانیه (پیش‌فرض 10)
    --only        فقط تگ‌های مشخصی رو تست کن، مثلا: --only accounts acl
    --skip-write  اگر بذاری، فقط GET ها تست میشن (برای جلوگیری از ساخت/حذف داده واقعی)
    --report      مسیر فایل json خروجی گزارش کامل (پیش‌فرض api_report.json)
    --html        مسیر فایل html خروجی گزارش قابل‌مشاهده در مرورگر (پیش‌فرض api_report.html)
"""

import argparse
import json
import re
import sys
import time
import copy
from urllib.parse import urljoin

try:
    import yaml
except ImportError:
    print("پکیج pyyaml نصب نیست. اجرا کن: pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("پکیج requests نصب نیست. اجرا کن: pip install requests")
    sys.exit(1)


# ---------- رنگ‌ها برای خروجی ترمینال ----------
class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def color(text, c):
    return f"{c}{text}{C.END}"


# ---------- کمک‌تابع‌ها برای resolve کردن $ref و ساخت داده‌ی نمونه ----------

def resolve_ref(spec, ref):
    """یک $ref مثل '#/components/schemas/Login' رو به آبجکت واقعی تبدیل می‌کنه"""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for p in parts:
        node = node[p]
    return node


def merge_all_of(spec, schema, seen):
    """ترکیب allOf ها در یک دیکشنری واحد"""
    merged = {"type": "object", "properties": {}, "required": []}
    for sub in schema.get("allOf", []):
        resolved = resolve_schema(spec, sub, seen)
        if resolved.get("type") == "object":
            merged["properties"].update(resolved.get("properties", {}))
            merged["required"] = list(set(merged["required"] + resolved.get("required", [])))
        else:
            return resolved
    return merged


def resolve_schema(spec, schema, seen=None):
    """schema رو resolve می‌کنه (شامل $ref و allOf)، جلوی loop بی‌نهایت رو هم می‌گیره"""
    if seen is None:
        seen = set()
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen:
            return {"type": "object", "properties": {}}
        seen = seen | {ref}
        return resolve_schema(spec, resolve_ref(spec, ref), seen)
    if "allOf" in schema:
        return merge_all_of(spec, schema, seen)
    return schema


# مقادیر نمونه بر اساس نام فیلد (برای داده‌های واقع‌گرایانه‌تر)
FIELD_NAME_HINTS = {
    "phone_number": "09120000000",
    "phone": "09120000000",
    "password": "TestPass123!",
    "old_password": "TestPass123!",
    "new_password": "NewTestPass123!",
    "confirm_password": "NewTestPass123!",
    "code": "123456",
    "first_name": "تست",
    "last_name": "کاربر",
    "email": "test@example.com",
    "title": "تست",
    "name": "تست",
    "description": "توضیحات تست",
    "address": "آدرس تست",
}


# الگوهای جایگزین بر اساس بخشی از اسم فیلد (وقتی format توی schema مشخص نشده)
FIELD_NAME_SUBSTRING_HINTS = [
    ("date", "2026-01-01"),
    ("time", "10:00:00"),
    ("email", "test@example.com"),
    ("slug", "test-slug"),
    ("random_code", "TEST01"),
    ("price", 1000),
    ("amount", 1000),
    ("duration", 30),
]


def sample_value_for(spec, field_name, schema, seen=None):
    schema = resolve_schema(spec, schema, seen)
    stype = schema.get("type")

    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    if field_name and field_name.lower() in FIELD_NAME_HINTS:
        val = FIELD_NAME_HINTS[field_name.lower()]
        max_len = schema.get("maxLength")
        if max_len and isinstance(val, str):
            return val[:max_len]
        return val

    fmt = schema.get("format")

    # اگه format توی schema مشخص نشده بود، از روی اسم فیلد حدس بزن
    # (مثلا اسم "date" هست ولی format:date نوشته نشده -> جلوی ارسال "تست" به‌جای تاریخ رو می‌گیره)
    if field_name and stype == "string" and not fmt:
        low = field_name.lower()
        for pattern, hint_val in FIELD_NAME_SUBSTRING_HINTS:
            if pattern in low and isinstance(hint_val, str):
                max_len = schema.get("maxLength")
                if max_len:
                    return hint_val[:max_len]
                return hint_val

    if field_name and stype in ("integer", "number"):
        low = field_name.lower()
        for pattern, hint_val in FIELD_NAME_SUBSTRING_HINTS:
            if pattern in low and isinstance(hint_val, (int, float)):
                return hint_val

    if stype == "string":
        if fmt == "date":
            return "2026-01-01"
        if fmt == "date-time":
            return "2026-01-01T10:00:00Z"
        if fmt == "time":
            return "10:00:00"
        if fmt == "uri":
            return "https://example.com/test.png"
        if fmt == "email":
            return "test@example.com"
        val = "تست"
        max_len = schema.get("maxLength")
        if max_len:
            return val[: max(1, max_len)]
        return val

    if stype == "integer":
        minimum = schema.get("minimum", 1)
        return minimum if minimum else 1

    if stype == "number":
        return 1.0

    if stype == "boolean":
        return True

    if stype == "array":
        items_schema = schema.get("items", {})
        return [sample_value_for(spec, field_name, items_schema, seen)]

    if stype == "object" or "properties" in schema:
        return build_sample_body(spec, schema, seen)

    # نوع نامشخص -> رشته‌ی خالی امن
    return "test"


def build_sample_body(spec, schema, seen=None):
    """بر اساس یک schema object، یک دیکشنری نمونه شامل فیلدهای لازم می‌سازه"""
    schema = resolve_schema(spec, schema, seen)
    if schema.get("type") != "object" and "properties" not in schema:
        return sample_value_for(spec, None, schema, seen)

    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    body = {}
    for field_name, field_schema in props.items():
        resolved_field = resolve_schema(spec, field_schema, seen)
        # فیلدهای readOnly رو تو بدنه‌ی درخواست نمی‌فرستیم (سرور خودش پر می‌کنه)
        if resolved_field.get("readOnly"):
            continue
        # فقط فیلدهای اجباری + چند فیلد رایج رو پر می‌کنیم تا درخواست سبک بمونه
        if field_name in required or resolved_field.get("writeOnly"):
            body[field_name] = sample_value_for(spec, field_name, field_schema, seen)
    return body


def get_example_from_content(spec, content):
    """اگر توی requestBody یک 'examples' واقعی نوشته شده باشه، همون رو برمی‌گردونه"""
    if not content:
        return None
    json_content = content.get("application/json")
    if not json_content:
        return None
    if "example" in json_content:
        return json_content["example"]
    examples = json_content.get("examples")
    if examples:
        first_key = next(iter(examples))
        return examples[first_key].get("value")
    return None


# ---------- ساخت لیست عملیات از spec ----------

def extract_operations(spec):
    ops = []
    for path, path_item in spec.get("paths", {}).items():
        for method in ["get", "post", "put", "patch", "delete"]:
            if method not in path_item:
                continue
            op = path_item[method]
            ops.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "operationId": op.get("operationId", ""),
                    "tags": op.get("tags", []),
                    "parameters": op.get("parameters", []),
                    "requestBody": op.get("requestBody"),
                    "security": op.get("security", []),
                }
            )
    return ops


def build_url(base_url, path, path_param_value):
    # جایگزینی پارامترهای مسیر مثل {id} یا {slug}
    def repl(match):
        return str(path_param_value)

    filled_path = re.sub(r"\{[^}]+\}", repl, path)
    return urljoin(base_url.rstrip("/") + "/", filled_path.lstrip("/"))


def build_query_params(spec, parameters, path_param_value):
    params = {}
    for p in parameters:
        if p.get("in") != "query":
            continue
        if p.get("required"):
            schema = p.get("schema", {})
            params[p["name"]] = sample_value_for(spec, p["name"], schema)
    return params


def needs_auth(security):
    """اگه توی security فقط یک {} خالی باشه یعنی auth اختیاریه، در غیر این صورت لازمه"""
    if not security:
        return False
    for s in security:
        if s == {}:
            return False
    return True


def find_login_field_names(spec, login_path, login_method="post"):
    """اسم واقعی فیلدهای شماره‌تلفن/یوزرنیم و پسورد رو مستقیم از schema لاگین می‌خونه
    (به‌جای حدس زدن)، تا دقیقاً همون چیزی که سرور انتظار داره فرستاده بشه."""
    op = spec["paths"][login_path].get(login_method, {})
    content = op.get("requestBody", {}).get("content", {})
    schema = content.get("application/json", {}).get("schema")
    if not schema:
        return None, None
    resolved = resolve_schema(spec, schema)
    props = resolved.get("properties", {})
    phone_field = None
    password_field = None
    for name in props:
        low = name.lower()
        if password_field is None and "password" in low:
            password_field = name
        if phone_field is None and ("phone" in low or "username" in low or "email" in low):
            phone_field = name
    return phone_field, password_field


def try_login(spec, base_url, phone, password, timeout):
    """با فیلدهای واقعیِ خوانده‌شده از schema، لاگین می‌کنه و توکن JWT می‌گیره.
    اگه شکست بخوره، خطای کامل سرور رو چاپ می‌کنه (نه یه پیام حدسی)."""
    login_path = None
    for path, item in spec.get("paths", {}).items():
        if "login" in path.lower() and "post" in item:
            login_path = path
            break
    if not login_path:
        print(color("مسیر login توی اسکیما پیدا نشد؛ بدون توکن ادامه می‌دیم.", C.YELLOW))
        return None

    phone_field, password_field = find_login_field_names(spec, login_path)
    if not phone_field or not password_field:
        print(color("نتونستم اسم فیلدهای لاگین رو از schema تشخیص بدم؛ بدون توکن ادامه می‌دیم.", C.YELLOW))
        return None

    url = build_url(base_url, login_path, 1)
    payload = {phone_field: phone, password_field: password}

    print(color(f"در حال لاگین با فیلدهای '{phone_field}' و '{password_field}' ...", C.CYAN))

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        print(color(f"خطا در اتصال برای لاگین: {e}", C.RED))
        return None

    if resp.status_code >= 400:
        print(color(f"لاگین ناموفق بود. status: {resp.status_code}", C.RED))
        try:
            print(color(json.dumps(resp.json(), ensure_ascii=False, indent=2), C.RED))
        except Exception:
            print(color(resp.text[:1000], C.RED))
        print(color("ادامه‌ی تست بدون توکن (اندپوینت‌های نیازمند لاگین همگی 401 می‌گیرن).", C.YELLOW))
        return None

    data = {}
    try:
        data = resp.json()
    except Exception:
        print(color("لاگین موفق بود ولی پاسخ JSON نبود؛ نمی‌تونم توکن رو استخراج کنم.", C.YELLOW))
        return None

    for token_key in ("access", "token", "access_token", "key", "jwt"):
        if token_key in data:
            print(color(f"لاگین موفق شد؛ توکن از فیلد '{token_key}' گرفته شد و برای بقیه‌ی درخواست‌ها استفاده می‌شه.", C.GREEN))
            return data[token_key]

    # شاید توکن تو یک ساب‌کی دیگه باشه (مثلا nested)
    for v in data.values():
        if isinstance(v, str) and v.count(".") == 2:
            print(color("لاگین موفق شد؛ یک مقدار شبیه JWT در پاسخ پیدا شد و استفاده می‌شه.", C.GREEN))
            return v

    print(color("لاگین موفق بود (status 2xx) ولی هیچ توکنی تو پاسخ پیدا نشد. پاسخ کامل:", C.YELLOW))
    print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
    return None


def run_tests(args):
    with open(args.spec, encoding="utf-8") as f:
        if args.spec.endswith(".json"):
            spec = json.load(f)
        else:
            spec = yaml.safe_load(f)

    operations = extract_operations(spec)
    if args.only:
        operations = [op for op in operations if any(t in op["tags"] for t in args.only)]
    if args.skip_write:
        operations = [op for op in operations if op["method"] == "GET"]

    token = args.token
    if not token and args.phone and args.password:
        token = try_login(spec, args.base_url, args.phone, args.password, args.timeout)

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    results = []
    print(color(f"\nشروع تست {len(operations)} اندپوینت روی {args.base_url}\n", C.BOLD + C.CYAN))

    for i, op in enumerate(operations, 1):
        path, method = op["path"], op["method"]
        url = build_url(args.base_url, path, args.id)
        query_params = build_query_params(spec, op["parameters"], args.id)

        req_headers = dict(headers)
        auth_required = needs_auth(op["security"])
        if auth_required and not token:
            pass  # بدون توکن هم می‌فرستیم؛ انتظار 401/403 داریم و در گزارش مشخص می‌کنیم

        json_body = None
        if method in ("POST", "PUT", "PATCH") and op["requestBody"]:
            content = op["requestBody"].get("content", {})
            example = get_example_from_content(spec, content)
            if example is not None:
                json_body = example
            else:
                schema = content.get("application/json", {}).get("schema")
                if schema:
                    json_body = build_sample_body(spec, schema)

        start = time.time()
        error_msg = None
        status_code = None
        try:
            resp = requests.request(
                method,
                url,
                json=json_body,
                params=query_params,
                headers=req_headers,
                timeout=args.timeout,
            )
            status_code = resp.status_code
            body_snippet = ""
            try:
                body_snippet = json.dumps(resp.json(), ensure_ascii=False)[:300]
            except Exception:
                body_snippet = resp.text[:300]
        except requests.RequestException as e:
            error_msg = str(e)
            body_snippet = ""

        elapsed_ms = int((time.time() - start) * 1000)

        if error_msg:
            status_label = "CONN_ERROR"
            tag_color = C.RED
        elif status_code >= 500:
            status_label = str(status_code)
            tag_color = C.RED
        elif status_code >= 400:
            # اگر auth لازم بوده و توکن نداشتیم، 401/403 طبیعیه نه باگ
            if status_code in (401, 403) and (auth_required and not token):
                status_label = f"{status_code} (نیاز به لاگین)"
                tag_color = C.YELLOW
            else:
                status_label = str(status_code)
                tag_color = C.YELLOW
        else:
            status_label = str(status_code)
            tag_color = C.GREEN

        results.append(
            {
                "method": method,
                "path": path,
                "url": url,
                "tags": op["tags"],
                "status_code": status_code,
                "error": error_msg,
                "elapsed_ms": elapsed_ms,
                "response_snippet": body_snippet,
                "auth_required": auth_required,
                "had_token": bool(token),
                "request_body": json_body,
            }
        )

        print(
            f"[{i:>3}/{len(operations)}] {method:<6} {path:<55} -> "
            + color(status_label, tag_color)
            + f"  ({elapsed_ms}ms)"
        )

    return results


def print_summary(results):
    total = len(results)
    ok = sum(1 for r in results if r["status_code"] and r["status_code"] < 400)
    client_err = sum(
        1
        for r in results
        if r["status_code"]
        and 400 <= r["status_code"] < 500
        and not (r["status_code"] in (401, 403) and r["auth_required"] and not r["had_token"])
    )
    auth_needed = sum(
        1
        for r in results
        if r["status_code"] in (401, 403) and r["auth_required"] and not r["had_token"]
    )
    server_err = sum(1 for r in results if r["status_code"] and r["status_code"] >= 500)
    conn_err = sum(1 for r in results if r["error"])

    print("\n" + color("=" * 60, C.CYAN))
    print(color("خلاصه‌ی نتایج", C.BOLD))
    print(color("=" * 60, C.CYAN))
    print(f"کل اندپوینت‌ها          : {total}")
    print(color(f"موفق (2xx/3xx)          : {ok}", C.GREEN))
    print(color(f"نیازمند لاگین (401/403) : {auth_needed}", C.YELLOW))
    print(color(f"خطای کلاینت (4xx)       : {client_err}", C.YELLOW))
    print(color(f"خطای سرور (5xx)         : {server_err}", C.RED))
    print(color(f"خطای اتصال              : {conn_err}", C.RED))

    real_errors = [
        r
        for r in results
        if (r["error"])
        or (r["status_code"] and r["status_code"] >= 500)
        or (
            r["status_code"]
            and 400 <= r["status_code"] < 500
            and not (r["status_code"] in (401, 403) and r["auth_required"] and not r["had_token"])
        )
    ]

    if real_errors:
        print("\n" + color("جزئیات خطاهایی که احتمالاً باگ واقعی هستن:", C.BOLD + C.RED))
        for r in real_errors:
            print(color(f"\n{r['method']} {r['path']}", C.RED))
            print(f"  status: {r['status_code'] or r['error']}")
            print(f"  response: {r['response_snippet']}")
            if r["request_body"]:
                print(f"  sent body: {json.dumps(r['request_body'], ensure_ascii=False)[:300]}")
    else:
        print(color("\nهیچ خطای واقعی‌ای پیدا نشد. عالیه!", C.GREEN))


def write_html_report(results, path):
    rows = []
    for r in results:
        status = r["status_code"] or "ERR"
        if r["error"]:
            css = "err"
        elif r["status_code"] and r["status_code"] >= 500:
            css = "err"
        elif r["status_code"] and r["status_code"] >= 400:
            if r["status_code"] in (401, 403) and r["auth_required"] and not r["had_token"]:
                css = "auth"
            else:
                css = "warn"
        else:
            css = "ok"
        rows.append(
            f"""<tr class="{css}">
            <td>{r['method']}</td><td dir="ltr">{r['path']}</td>
            <td>{', '.join(r['tags'])}</td><td>{status}</td>
            <td>{r['elapsed_ms']}ms</td>
            <td><pre>{(r['error'] or r['response_snippet'])[:400]}</pre></td>
            </tr>"""
        )
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8">
<title>گزارش تست API</title>
<style>
body {{ font-family: Tahoma, sans-serif; background:#0f172a; color:#e2e8f0; padding:20px;}}
table {{ width:100%; border-collapse: collapse; }}
th, td {{ padding:8px; border:1px solid #334155; text-align:right; font-size:13px; }}
th {{ background:#1e293b; }}
tr.ok {{ background:#052e1c; }}
tr.warn {{ background:#3f2d05; }}
tr.auth {{ background:#1a2a4a; }}
tr.err {{ background:#3f0505; }}
pre {{ white-space: pre-wrap; word-break: break-all; margin:0; direction:ltr; text-align:left;}}
h1 {{ color:#34d399; }}
</style>
</head>
<body>
<h1>گزارش تست API نارژین</h1>
<p>سبز: موفق | آبی: نیاز به لاگین | زرد: خطای کلاینت | قرمز: خطای سرور/اتصال</p>
<table>
<tr><th>Method</th><th>Path</th><th>Tags</th><th>Status</th><th>Time</th><th>Response</th></tr>
{''.join(rows)}
</table>
</body>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="تست خودکار همه‌ی اندپوینت‌های API بر اساس OpenAPI schema")
    parser.add_argument("--spec", default="Project_API_2_.yaml", help="مسیر فایل schema")
    parser.add_argument("--base-url", required=True, help="آدرس ریشه‌ی سرور، مثلا http://127.0.0.1:8000")
    parser.add_argument("--phone", help="شماره تلفن برای لاگین خودکار")
    parser.add_argument("--password", help="پسورد برای لاگین خودکار")
    parser.add_argument("--token", help="توکن JWT آماده (اگر بدی، لاگین خودکار انجام نمیشه)")
    parser.add_argument("--id", default="1", help="مقدار جایگزین پارامترهای مسیر مثل {id}")
    parser.add_argument("--timeout", type=float, default=10, help="تایم‌اوت هر ریکوئست")
    parser.add_argument("--only", nargs="*", help="فقط این تگ‌ها تست بشن، مثلا: --only accounts acl")
    parser.add_argument("--skip-write", action="store_true", help="فقط GET ها تست بشن")
    parser.add_argument("--report", default="api_report.json", help="مسیر فایل گزارش JSON")
    parser.add_argument("--html", default="api_report.html", help="مسیر فایل گزارش HTML")
    args = parser.parse_args()

    results = run_tests(args)
    print_summary(results)

    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    write_html_report(results, args.html)

    print(f"\nگزارش کامل JSON در: {args.report}")
    print(f"گزارش تصویری HTML در: {args.html}")


if __name__ == "__main__":
    main()