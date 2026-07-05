#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل API با یک کاربر واقعی (صاحب سالن) + گزارش HTML
==========================================================
این اسکریپت شبیه‌سازی کاربران فیک نمی‌کنه؛ فقط با اطلاعات لاگین/ثبت‌نامی که
خودتون میدید، وارد میشه و مثل یک صاحب سالن واقعی، تقریبا همه‌ی APIهای اصلی
پروژه رو به ترتیب منطقی صدا می‌زنه: ساخت کسب‌وکار، کارمند، سرویس، ساعت کاری،
اسلات، پکیج، نوبت، کامنت، و بعد لیست‌ها/گزارش‌ها/داشبورد و... .

در پایان یک فایل HTML می‌سازه (با نمودار Chart.js) که وضعیت هر API رو
(موفق/ناموفق، زمان پاسخ، پیام خطا در صورت وجود) نشون میده.

اجرا:
    pip install requests
    python narjin_owner_test.py --base-url http://127.0.0.1:8000

بعدش ازتون می‌پرسه که می‌خواید ثبت‌نام کنید یا با حساب موجود لاگین کنید،
و اطلاعات لازم رو (نام، شماره، پسورد) می‌گیره.

اگه نمی‌خواید تعاملی باشه، می‌تونید مستقیم بدید:
    python narjin_owner_test.py --base-url http://127.0.0.1:8000 \\
        --mode login --phone 09121234567 --password "MyPass123"
"""

import argparse
import json
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import date, timedelta
from getpass import getpass
from typing import Optional, Dict, Any, List

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 20


@dataclass
class ApiCall:
    label: str          # اسم قابل‌فهم فارسی برای گزارش
    method: str
    path: str
    status: int
    ok: bool
    elapsed_ms: float
    request_body: Optional[dict] = None
    response_preview: str = ""
    error: Optional[str] = None


class OwnerFlow:
    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.calls: List[ApiCall] = []

        self.user_id = None
        self.business_id = None
        self.employee_id = None
        self.service_id = None
        self.slot_id = None
        self.package_id = None
        self.comment_id = None
        self.appointment_id = None

    # ---------------------------------------------------------------
    def _call(self, label: str, method: str, path: str, auth: bool = True,
               json_body: Optional[dict] = None, params: Optional[dict] = None) -> Optional[requests.Response]:
        url = f"{self.base_url}{path}"
        headers = {}
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        start = time.perf_counter()
        status, ok, error, resp, preview = 0, False, None, None, ""
        try:
            resp = self.session.request(method, url, headers=headers, json=json_body,
                                         params=params, timeout=self.timeout)
            status = resp.status_code
            ok = 200 <= status < 300
            body_text = resp.text
            preview = body_text[:400] + ("...(truncated)" if len(body_text) > 400 else "")
        except requests.RequestException as e:
            error = str(e)[:300]
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.calls.append(ApiCall(
            label=label, method=method, path=path, status=status, ok=ok,
            elapsed_ms=elapsed_ms, request_body=json_body,
            response_preview=preview, error=error,
        ))
        return resp

    @staticmethod
    def _extract_token(data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        for key in ("access", "access_token", "token", "jwt", "accessToken"):
            if key in data and isinstance(data[key], str):
                return data[key]
        for v in data.values():
            if isinstance(v, dict):
                found = OwnerFlow._extract_token(v)
                if found:
                    return found
        return None

    @staticmethod
    def _try_id(resp: Optional[requests.Response]):
        if resp is None:
            return None
        try:
            return resp.json().get("id")
        except Exception:
            return None

    # ---------------------------------------------------------------
    # احراز هویت
    # ---------------------------------------------------------------
    def register(self, first_name: str, last_name: str, phone: str, password: str) -> bool:
        payload = {"first_name": first_name, "last_name": last_name,
                   "phone_number": phone, "password": password}
        resp = self._call("ثبت‌نام کاربر", "POST", "/accounts/register/", auth=False, json_body=payload)
        return resp is not None and resp.status_code == 201

    def login(self, phone: str, password: str) -> bool:
        payload = {"phone_number": phone, "password": password}
        resp = self._call("ورود (لاگین)", "POST", "/accounts/login/", auth=False, json_body=payload)
        if resp is None or not resp.ok:
            return False
        try:
            data = resp.json()
        except ValueError:
            return False
        self.access_token = self._extract_token(data)
        return self.access_token is not None

    # ---------------------------------------------------------------
    # سناریوی کامل «صاحب سالن»
    # ---------------------------------------------------------------
    def run_owner_scenario(self):
        # پروفایل کاربر (برای گرفتن user_id)
        resp = self._call("پروفایل کاربر", "GET", "/dashboard/users/profile/")
        self.user_id = None
        if resp is not None and resp.ok:
            try:
                self.user_id = resp.json().get("id")
            except Exception:
                pass

        # آیا از قبل کسب‌وکاری داره؟
        me_resp = self._call("کسب‌وکار من (بررسی وجود)", "GET", "/business/me/")
        if me_resp is not None and me_resp.ok:
            try:
                self.business_id = me_resp.json().get("id")
            except Exception:
                pass

        if not self.business_id:
            payload = {
                "name": "سالن زیبایی نارژین",
                "slug": f"narjin-salon-{int(time.time())}",
                "business_type": "salon",
                "address": "تهران، خیابان ولیعصر، پلاک ۱۲۰",
                "phone_number": "02188990011",
            }
            resp = self._call("ساخت کسب‌وکار", "POST", "/business/create/", json_body=payload)
            self.business_id = self._try_id(resp)

        # ساخت کارمند (خودِ صاحب سالن به‌عنوان کارمند)
        if self.user_id:
            payload = {"user_id": self.user_id, "skill": "مدیریت و پذیرش"}
            resp = self._call("ساخت کارمند", "POST", "/business/employees/create/", json_body=payload)
            self.employee_id = self._try_id(resp)

        # ساخت سرویس
        payload = {
            "name": "کوتاهی مو + اصلاح صورت",
            "price": "450000",
            "description": "کوتاهی مو، اصلاح صورت و مدل‌دهی حرفه‌ای",
            "duration": "00:45:00",
            "employee_id": self.employee_id,
        }
        resp = self._call("ساخت سرویس", "POST", "/business/services/create/", json_body=payload)
        self.service_id = self._try_id(resp)

        # ساعت کاری
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        payload = {"day": tomorrow, "opening_time": "09:00:00", "closing_time": "20:00:00"}
        self._call("ثبت ساعت کاری", "POST", "/working_hours/create/", json_body=payload)

        # اسلات زمانی
        if self.service_id:
            payload = {"service_id": self.service_id, "date": tomorrow, "start_time": "11:00:00"}
            resp = self._call("ساخت اسلات نوبت‌دهی", "POST", "/business/slots/create/", json_body=payload)
            self.slot_id = self._try_id(resp)

        # پکیج
        if self.business_id:
            payload = {
                "business_id": self.business_id,
                "name": "پکیج داماد",
                "desc": "کوتاهی مو، اصلاح، ماساژ صورت",
                "total_price": "950000",
                "service_ids": [self.service_id] if self.service_id else [],
            }
            resp = self._call("ساخت پکیج", "POST", "/packages/create/", json_body=payload)
            self.package_id = self._try_id(resp)

        # کامنت / نظر
        payload = {
            "target_type": "business",
            "content": "تجربه خیلی خوبی بود، کیفیت کار عالی بود.",
            "rating": 5,
            "business": self.business_id,
            "service": None,
        }
        resp = self._call("ثبت نظر مشتری", "POST", "/comments/", json_body=payload)
        self.comment_id = self._try_id(resp)

        # زمان‌های آزاد
        if self.service_id:
            self._call("زمان‌های آزاد سرویس", "GET", "/business/available-times/",
                        params={"date": tomorrow, "service_id": self.service_id})

        # گرفتن نوبت
        if self.service_id:
            payload = {"service_id": self.service_id, "employee_id": self.employee_id,
                       "time_slot_id": self.slot_id}
            resp = self._call("ثبت نوبت (Appointment)", "POST", "/reservations/my-appointments/", json_body=payload)
            self.appointment_id = self._try_id(resp)

        # --- لیست‌ها و گزارش‌ها ---
        gets = [
            ("لیست کسب‌وکارها", "/business/"),
            ("لیست سرویس‌ها", "/business/services/"),
            ("لیست کارمندها", "/business/employees/"),
            ("لیست اسلات‌ها", "/business/slots/"),
            ("لیست پکیج‌ها", "/packages/"),
            ("پکیج‌های من", "/packages/user/"),
            ("لیست نظرات", "/comments/"),
            ("ساعات کاری من", "/working_hours/user/"),
            ("نوبت‌های من", "/reservations/my-appointments/"),
            ("داشبورد", "/dashboard/"),
            ("گزارش نوبت‌ها", "/reports/appointments/"),
            ("گزارش مالی", "/reports/financial/"),
            ("پرفروش‌ترین سرویس‌ها", "/reports/top-services/"),
            ("پلن‌های اشتراک (لندینگ)", "/landing/plans/"),
            ("مقالات لندینگ", "/landing/article/"),
            ("وضعیت اشتراک", "/landing/subscription/"),
            ("اسلایدرهای عمومی", "/sliders/"),
            ("اسلایدرهای من", "/sliders/user/"),
            ("کیف پول", "/payments/wallet/"),
            ("تراکنش‌های کیف پول", "/payments/wallet/transactions/"),
            ("کارت‌های بانکی من", "/payments/cards/number/"),
            ("پرداخت‌های دستی", "/payments/manual-payments/"),
            ("مجوزهای ACL", "/acl/permissions/"),
            ("مجوزهای کاربران", "/acl/user-permissions/"),
        ]
        for label, path in gets:
            self._call(label, "GET", path)

        if self.business_id:
            self._call("جزئیات کسب‌وکار من", "GET", f"/business/{self.business_id}/")


# ----------------------------------------------------------------------------
# ساخت گزارش HTML
# ----------------------------------------------------------------------------
def build_html_report(calls: List[ApiCall], base_url: str, output_path: str):
    total = len(calls)
    ok_count = sum(1 for c in calls if c.ok)
    fail_count = total - ok_count
    avg_ms = round(sum(c.elapsed_ms for c in calls) / total, 1) if total else 0
    success_rate = round(100 * ok_count / total, 1) if total else 0

    labels_json = json.dumps([c.label for c in calls], ensure_ascii=False)
    times_json = json.dumps([round(c.elapsed_ms, 1) for c in calls])
    colors_json = json.dumps(["#2e7d32" if c.ok else "#c62828" for c in calls])

    rows_html = ""
    for c in calls:
        status_badge = f'<span class="badge {"ok" if c.ok else "fail"}">{c.status if c.status else "ERR"}</span>'
        error_html = ""
        if not c.ok:
            detail = c.error or c.response_preview or "بدون جزئیات"
            error_html = f'<div class="error-detail">{_esc(detail)}</div>'
        rows_html += f"""
        <tr class="{'row-ok' if c.ok else 'row-fail'}">
            <td>{_esc(c.label)}</td>
            <td><code>{c.method}</code></td>
            <td><code>{_esc(c.path)}</code></td>
            <td>{status_badge}</td>
            <td>{round(c.elapsed_ms, 1)} ms</td>
            <td>{error_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>گزارش تست API نارژین</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
  body {{ font-family: 'Vazirmatn', Tahoma, sans-serif; background:#f5f3ee; margin:0; padding:24px; color:#1f2d24; }}
  h1 {{ color:#0f3d2e; }}
  .summary {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }}
  .card {{ background:#fff; border-radius:12px; padding:16px 24px; box-shadow:0 1px 4px rgba(0,0,0,.08); min-width:150px; }}
  .card .num {{ font-size:28px; font-weight:700; color:#0f3d2e; }}
  .card .label {{ color:#666; font-size:13px; margin-top:4px; }}
  .chart-wrap {{ background:#fff; border-radius:12px; padding:20px; margin-bottom:24px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  th, td {{ padding:10px 14px; text-align:right; border-bottom:1px solid #eee; font-size:14px; vertical-align:top; }}
  th {{ background:#0f3d2e; color:#fff; position:sticky; top:0; }}
  .row-fail {{ background:#fff5f5; }}
  .badge {{ padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; color:#fff; }}
  .badge.ok {{ background:#2e7d32; }}
  .badge.fail {{ background:#c62828; }}
  .error-detail {{ font-family:monospace; font-size:11px; color:#b71c1c; white-space:pre-wrap; max-width:420px; }}
  code {{ background:#f0efe9; padding:2px 6px; border-radius:4px; }}
</style>
</head>
<body>
<h1>گزارش تست کامل API — {_esc(base_url)}</h1>

<div class="summary">
  <div class="card"><div class="num">{total}</div><div class="label">کل درخواست‌ها</div></div>
  <div class="card"><div class="num" style="color:#2e7d32">{ok_count}</div><div class="label">موفق</div></div>
  <div class="card"><div class="num" style="color:#c62828">{fail_count}</div><div class="label">ناموفق</div></div>
  <div class="card"><div class="num">{success_rate}%</div><div class="label">نرخ موفقیت</div></div>
  <div class="card"><div class="num">{avg_ms} ms</div><div class="label">میانگین زمان پاسخ</div></div>
</div>

<div class="chart-wrap">
  <canvas id="chart" height="90"></canvas>
</div>

<table>
  <thead>
    <tr><th>API</th><th>Method</th><th>Path</th><th>وضعیت</th><th>زمان پاسخ</th><th>جزئیات خطا</th></tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>

<script>
  const ctx = document.getElementById('chart');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {labels_json},
      datasets: [{{
        label: 'زمان پاسخ (ms)',
        data: {times_json},
        backgroundColor: {colors_json},
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ autoSkip: false, maxRotation: 80, minRotation: 60 }} }},
        y: {{ title: {{ display: true, text: 'میلی‌ثانیه' }} }}
      }}
    }}
  }});
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="تست کامل API با یک کاربر واقعی + گزارش HTML")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--mode", choices=["register", "login"], default=None,
                         help="اگه ندید، به‌صورت تعاملی می‌پرسه")
    parser.add_argument("--phone", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--first-name", default=None)
    parser.add_argument("--last-name", default=None)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", default="narjin_api_report.html")
    parser.add_argument("--no-open", action="store_true", help="گزارش رو خودکار تو مرورگر باز نکن")
    args = parser.parse_args()

    print(f"تست روی: {args.base_url}\n")

    mode = args.mode
    if mode is None:
        ans = input("می‌خواید (1) ثبت‌نام کنید یا (2) با حساب موجود لاگین کنید؟ [1/2]: ").strip()
        mode = "register" if ans == "1" else "login"

    phone = args.phone or input("شماره موبایل (مثلا 09121234567): ").strip()
    password = args.password or getpass("رمز عبور: ")

    flow = OwnerFlow(args.base_url, args.timeout)

    if mode == "register":
        first_name = args.first_name or input("نام: ").strip()
        last_name = args.last_name or input("نام خانوادگی: ").strip()
        print("\nدر حال ثبت‌نام...")
        if not flow.register(first_name, last_name, phone, password):
            last = flow.calls[-1]
            print(f"❌ ثبت‌نام ناموفق بود. status={last.status}\nپاسخ سرور: {last.response_preview or last.error}")
            print("در هر صورت الان تلاش می‌کنیم با همین شماره/پسورد لاگین کنیم (شاید از قبل ثبت‌نام شده)...")

    print("در حال ورود (لاگین)...")
    if not flow.login(phone, password):
        last = flow.calls[-1]
        print(f"❌ لاگین ناموفق بود. status={last.status}\nپاسخ سرور: {last.response_preview or last.error}")
        print("بدون توکن معتبر نمی‌تونیم ادامه بدیم. گزارش فقط شامل همین دو تلاش میشه.")
        build_html_report(flow.calls, args.base_url, args.output)
        print(f"\n📄 گزارش ذخیره شد در: {args.output}")
        return

    print("✅ لاگین موفق. توکن دریافت شد.\n")
    print("در حال اجرای سناریوی کامل صاحب سالن روی همه‌ی API ها...\n")
    flow.run_owner_scenario()

    ok = sum(1 for c in flow.calls if c.ok)
    print(f"\nتمام شد: {ok}/{len(flow.calls)} درخواست موفق بود.")

    build_html_report(flow.calls, args.base_url, args.output)
    print(f"📄 گزارش HTML ذخیره شد در: {args.output}")

    if not args.no_open:
        try:
            webbrowser.open(args.output)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nمتوقف شد.")