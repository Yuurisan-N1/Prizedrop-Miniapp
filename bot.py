import asyncio
import json
import os
import re
import signal
import ssl
import sys
import time
import urllib.parse
import uuid

import aiohttp

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Prize Drop Miniapp"
BASE_URL = "https://pricedropes.lovable.app"
REF_CODE = "6004380466"

HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/?tgWebAppStartParam={REF_CODE}",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; SM-S901B; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36",
}


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    text = str(value)
    for symbol in "[]|#!@$%^&*()-":
        text = text.replace(symbol, " ")
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def server_reason(value, limit):
    text = re.sub(r"^\s*Bad Request:\s*", "", clean_text(value, "no reason"))
    return shorten(text, "no reason", limit)


def number_of(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return float(fallback)
        except (TypeError, ValueError):
            return 0.0


def int_of(value, fallback):
    return int(number_of(value, fallback))


def format_duration(total):
    total = max(0, int(total))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def countdown(seconds):
    for remaining in range(max(0, int(seconds)), 0, -1):
        sys.stdout.write(f"\r{YELLOW}{BOLD}Next cycle starts in {format_duration(remaining)}{RESET}")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write(f"\r{YELLOW}{BOLD}Next cycle starts in {format_duration(0)}{RESET}")
    sys.stdout.flush()
    print()


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def normalize_proxy(raw):
    line = raw.strip()
    if not line:
        return None
    if "://" in line:
        return line
    parts = line.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return None


def load_config():
    if not os.path.isfile("config.json"):
        with open("config.json", "w", encoding="utf-8") as handle:
            json.dump({"settings": {"sleep_seconds": 3600, "join_giveaways": True}}, handle, indent=2)
            handle.write("\n")
    try:
        with open("config.json", encoding="utf-8") as handle:
            data = json.load(handle)
        settings = data.get("settings", {})
        sleep = int(settings.get("sleep_seconds", 3600))
        join_giveaways = bool(settings.get("join_giveaways", True))
        return sleep, join_giveaways
    except Exception:
        return 3600, True


def load_accounts():
    if not os.path.isfile("data.txt"):
        return []
    with open("data.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    accounts = []
    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        accounts.append(entry.split("|")[0].strip())
    return accounts


def load_proxies():
    if not os.path.isfile("proxy.txt"):
        return []
    with open("proxy.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    proxies = []
    for line in lines:
        normalized = normalize_proxy(line)
        if normalized:
            proxies.append(normalized)
    return proxies


def telegram_profile(init_data):
    profile = {"id": "", "username": "", "first_name": ""}
    try:
        for chunk in init_data.split("&"):
            if chunk.startswith("user="):
                payload = json.loads(urllib.parse.unquote(chunk[5:]))
                profile["id"] = str(payload.get("id") or "")
                profile["username"] = str(payload.get("username") or "")
                profile["first_name"] = str(payload.get("first_name") or "")
    except Exception:
        return profile
    return profile


class PrizeAccount:
    def __init__(self, init_data, proxy_url):
        self.init_data = init_data
        self.proxy_url = proxy_url
        self.profile = telegram_profile(init_data)
        self.state = {}
        self.session = None
        self.connector = None
        self.last_write = 0.0

    async def open(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.connector = aiohttp.TCPConnector(ssl=context)
        self.session = aiohttp.ClientSession(connector=self.connector, headers=HEADERS_BASE,
                                             cookie_jar=aiohttp.CookieJar(unsafe=True))

    async def close(self):
        if self.session is not None:
            await self.session.close()
        if self.connector is not None:
            await self.connector.close()

    async def pace(self):
        gap = 1.5 - (time.monotonic() - self.last_write)
        if gap > 0:
            await asyncio.sleep(gap)
        self.last_write = time.monotonic()

    async def request(self, method, path, payload=None):
        url = f"{BASE_URL}{path}"
        body_text = None
        if payload is not None:
            body_text = json.dumps(payload, separators=(",", ":"))
        headers = {"x-telegram-init-data": self.init_data, "referer": f"{BASE_URL}/"}
        last_error = None
        throttled = False
        if method == "POST":
            await self.pace()
        for attempt in range(4):
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with self.session.request(method, url, data=body_text, headers=headers,
                                                proxy=self.proxy_url, timeout=timeout) as response:
                    text = (await response.text()).strip()
                    if response.status == 429:
                        throttled = True
                        await asyncio.sleep(30)
                        continue
                    if not text:
                        return response.status, {}
                    try:
                        parsed = json.loads(text)
                    except json.JSONDecodeError:
                        return response.status, {"_raw": text[:400]}
                    if isinstance(parsed, dict):
                        self.capture_state(parsed)
                    return response.status, parsed
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(1.5 * (attempt + 1))
        if throttled:
            raise RuntimeError("rate limited")
        raise last_error if last_error else RuntimeError("request failed")

    async def get(self, path):
        return await self.request("GET", path)

    async def post(self, path, payload=None):
        return await self.request("POST", path, payload)

    def capture_state(self, body):
        if body.get("ticketBalance") is not None:
            self.state["ticketBalance"] = body.get("ticketBalance")
        if body.get("adsWatched") is not None:
            self.state["adsWatched"] = body.get("adsWatched")
        if body.get("spinsToday") is not None:
            self.state["spinsToday"] = body.get("spinsToday")

    async def handshake(self):
        code, body = await self.get("/api/public/account")
        if code != 200 or not isinstance(body, dict):
            return False
        self.state = dict(body)
        return True

    async def refresh(self):
        code, body = await self.get("/api/public/account")
        if code == 200 and isinstance(body, dict):
            self.state = dict(body)
            return self.state
        return None

    async def config(self):
        code, body = await self.get("/api/public/app-config")
        if code == 200 and isinstance(body, dict):
            return body
        return {}

    async def membership(self):
        code, body = await self.get("/api/public/membership")
        if code == 200 and isinstance(body, dict):
            return body
        return None

    async def label(self):
        name = self.profile.get("username") or self.profile.get("first_name") or self.profile.get("id")
        return shorten(name, "account", 20)


def error_text(payload, limit=22):
    return server_reason(payload.get("error") or payload.get("message") or payload.get("_raw"), limit)


async def run_membership(account):
    body = await account.membership()
    if body is None:
        log_yellow("The mandatory channel check could not be read from the server")
        return
    required = [item for item in (body.get("required") or []) if isinstance(item, dict)]
    pending = [item for item in required if not item.get("joined")]
    if body.get("ok") or not pending:
        log_green("Mandatory channel access was verified")
        return
    for channel in pending:
        name = shorten(channel.get("username") or channel.get("title"), "channel", 20)
        log_yellow(f"Channel {clean_text(name, 'channel')} is not joined yet")


async def run_ads(account, config, state):
    credited = 0.0
    settings = config.get("settings") if isinstance(config.get("settings"), dict) else {}
    networks = [item for item in (config.get("networks") or [])
                if isinstance(item, dict) and item.get("id")]
    if not networks:
        return credited
    network = networks[0]
    limit = int_of(settings.get("ads_daily_limit"), 0)
    wait = number_of(settings.get("ads_cooldown_seconds"), 15) + 2
    watched = int_of(state.get("adsWatched"), 0)
    room = (limit - watched) if limit > 0 else 20
    if room <= 0:
        return credited
    retries = 0
    for _ in range(room):
        code, body = await account.post("/api/public/rewards", {
            "action": "ad", "networkId": network.get("id"), "eventId": str(uuid.uuid4())})
        payload = body if isinstance(body, dict) else {}
        if code == 200 and payload.get("ok"):
            amount = number_of(payload.get("reward"), network.get("reward"))
            credited += amount
            watched = int_of(payload.get("adsWatched"), watched + 1)
            log_green(f"Ad reward credited {clean_text(amount, 0)} tickets")
            await asyncio.sleep(wait)
            continue
        detail = error_text(payload, 33)
        if "wait" in detail.lower() and retries < 2:
            retries += 1
            await asyncio.sleep(wait)
            continue
        log_yellow(f"Ad reward was refused with {clean_text(detail, 'no reason')}")
        break
    return credited


async def run_spins(account, config):
    credited = 0.0
    settings = config.get("settings") if isinstance(config.get("settings"), dict) else {}
    limit = int_of(settings.get("spin_daily_limit"), 0)
    for _ in range(limit if limit > 0 else 3):
        code, body = await account.post("/api/public/rewards", {"action": "spin"})
        payload = body if isinstance(body, dict) else {}
        if code == 200 and payload.get("ok"):
            amount = number_of(payload.get("reward"), 0)
            credited += amount
            log_green(f"Wheel spin credited {clean_text(amount, 0)} tickets")
            continue
        detail = error_text(payload, 27)
        log_yellow(f"The wheel spin was refused with {clean_text(detail, 'no reason')}")
        break
    return credited


async def run_tasks(account, config):
    credited = 0.0
    for task in config.get("tasks") or []:
        if not isinstance(task, dict) or not task.get("id"):
            continue
        name = shorten(task.get("title"), "task", 12)
        code, body = await account.post("/api/public/rewards",
                                        {"action": "task", "taskId": str(task.get("id"))})
        payload = body if isinstance(body, dict) else {}
        if code == 200 and payload.get("ok") and payload.get("reward") is not None:
            amount = number_of(payload.get("reward"), task.get("reward"))
            credited += amount
            log_green(f"Task {clean_text(name, 'task')} credited {clean_text(amount, 0)} tickets")
            continue
        detail = error_text(payload, 26)
        log_yellow(f"Task {clean_text(name, 'task')} was refused with {clean_text(detail, 'no reason')}")
    return credited


async def run_giveaways(account, config, state):
    tickets = number_of(state.get("ticketBalance"), 0)
    for giveaway in config.get("giveaways") or []:
        if not isinstance(giveaway, dict) or not giveaway.get("id"):
            continue
        if tickets < 1:
            break
        title = shorten(giveaway.get("title") or giveaway.get("prize"), "giveaway", 18)
        code, body = await account.post("/api/public/giveaway-entry",
                                        {"giveawayId": giveaway.get("id"), "tickets": int(tickets)})
        payload = body if isinstance(body, dict) else {}
        accepted = number_of(payload.get("accepted"), 0) if code == 200 else 0
        if accepted >= 1:
            tickets -= accepted
            log_green(f"Entered {clean_text(int(accepted), 0)} tickets into {clean_text(title, 'giveaway')}")
            continue
        detail = error_text(payload, 24)
        log_yellow(f"The giveaway entry was refused with {clean_text(detail, 'no reason')}")
        break


async def run_account(init_data, proxy_url, join_giveaways=True):
    account = PrizeAccount(init_data, proxy_url)
    await account.open()
    try:
        if not await account.handshake():
            log_red("The account session could not be opened by the server")
            return None
        label = await account.label()
        if proxy_url is not None:
            log_yellow(f"Using proxy {mask_proxy(proxy_url)}")
        log_green(f"Account {clean_text(label, 'account')} started the cycle")
        await run_membership(account)
        config = await account.config()
        credited = 0.0
        credited += await run_ads(account, config, account.state)
        credited += await run_spins(account, config)
        credited += await run_tasks(account, config)
        if join_giveaways:
            await run_giveaways(account, config, account.state)
        state = await account.refresh()
        if credited > 0:
            log_green(f"Cycle closed with {clean_text(credited, 0)} tickets credited on this run")
        else:
            log_yellow("Cycle closed without a new credit on this run")
        if state is not None:
            log_green(f"Ticket balance is now {clean_text(number_of(state.get('ticketBalance'), 0), 0)} tickets from {clean_text(int_of(state.get('adsWatched'), 0), 0)} views")
        return credited
    finally:
        await account.close()


async def main():
    show_banner(MY_PROJECT)
    sleep_seconds, join_giveaways = load_config()
    accounts = load_accounts()
    proxies = load_proxies()
    if not accounts:
        log_red("No account was found in data.txt")
        sys.exit(1)
    cycle = 0
    while True:
        cycle += 1
        log_green(f"Starting automation cycle number {clean_text(cycle, 0)}")
        for idx, init_data in enumerate(accounts):
            if idx > 0:
                print()
            proxy_url = proxies[idx % len(proxies)] if proxies else None
            try:
                await run_account(init_data, proxy_url, join_giveaways)
            except Exception as exc:
                log_red(f"Request to the server failed with {clean_text(type(exc).__name__, 'error')}")
        countdown(sleep_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        signal_handler(None, None)