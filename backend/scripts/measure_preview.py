"""Compare read-only API timings on two previews; credentials are never saved."""
import argparse
import getpass
import json
import time
from urllib.parse import urlsplit
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--role", choices=("admin", "label"), required=True)
    parser.add_argument("--repeat", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--baseline", action="store_true", help="Endpoint setara pada branch sebelum optimasi")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or parsed.path or parsed.query or parsed.fragment:
        parser.error("Gunakan origin HTTPS preview tanpa path.")
    email = input("Email akun pengujian: ").strip()
    password = getpass.getpass("Password (tidak ditampilkan/disimpan): ")
    routes = (["/label/dashboard", "/label/analytics?window=6", "/withdraw/label/computed",
               "/releases/?limit=5&include_revenue=false"] if args.role == "label" else
              ["/admin/work/queue?scope=all", "/admin/dashboard/metrics?period=month&include_money=false",
               "/admin/dashboard/in-progress", "/admin/analytics/monthly"])
    if args.baseline:
        routes = (["/label/dashboard", "/label/analytics?window=6", "/withdraw/label/computed", "/releases/"] if args.role == "label" else
                  ["/admin/work/queue?scope=my", "/admin/work/queue?scope=team", "/admin/dashboard/metrics?period=month",
                   "/admin/dashboard/in-progress", "/admin/analytics/monthly"])
    with httpx.Client(base_url=base, timeout=60, headers={"Origin": base}, follow_redirects=False) as session:
        response = session.post("/api/auth/login", json={"email": email, "password": password})
        del password
        if response.status_code != 200:
            raise SystemExit(f"Login gagal (HTTP {response.status_code}); isi respons tidak dicatat.")
        for iteration in range(args.repeat):
            for route in routes:
                start = time.perf_counter()
                try:
                    response = session.get("/api" + route)
                    result = {"iteration": iteration + 1, "route": route, "status": response.status_code,
                              "duration_ms": round((time.perf_counter() - start) * 1000),
                              "server_timing": response.headers.get("server-timing")}
                except httpx.HTTPError:
                    result = {"iteration": iteration + 1, "route": route, "error": "Request gagal/timeout"}
                print(json.dumps(result))
        session.post("/api/auth/logout")


if __name__ == "__main__":
    main()
