#!/usr/bin/env python3
"""
复用本地浏览器登录态（持久化 Profile 或 CDP 调试端口）抓取商品/软件/帖子评论区文本。
对 Steam 等开放接口平台支持免 Playwright 零依赖直连抓取。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_PROFILE_DIR = Path.home() / ".review-detox" / "browser_profile"

PLATFORM_SELECTORS = {
    "taobao": [
        "[class*='Comment--content']",
        "[class*='commentContent']",
        "[class*='Comment--item']",
        "[class*='commentCard']",
        "[class*='Comments--'] [class*='content--']",
        "[class*='rate-grid'] td.tm-col-master",
        ".tb-revbd li",
        "[class*='review'] [class*='content']",
    ],
    "jd": [
        ".comment-item .comment-con",
        ".comment-column .comment-con",
        "[class*='comment-con']",
    ],
    "xiaohongshu": [
        ".comment-item .content",
        "[class*='note-text']",
        "[class*='comment'] [class*='content']",
    ],
    "steam": [
        ".apphub_CardTextContent",
        ".review_box .content",
    ],
    "douban": [
        ".comment-item .short",
        ".review-short .short-content",
    ],
}

PRIMARY_REVIEW_TABS = ["查看全部评价", "全部评价", "宝贝评价", "累计评价", "商品评价"]
FILTER_REVIEW_TABS = ["追评", "中评", "差评"]
LOGIN_WALL_KEYWORDS = ("请登录", "扫码登录", "安全验证", "滑块", "验证码", "访问受限")
ECOMMERCE_PLATFORMS = {"taobao", "jd", "xiaohongshu"}


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "taobao.com" in host or "tmall.com" in host:
        return "taobao"
    if "jd.com" in host:
        return "jd"
    if "xiaohongshu.com" in host:
        return "xiaohongshu"
    if "steampowered.com" in host or "steamcommunity.com" in host:
        return "steam"
    if "douban.com" in host:
        return "douban"
    return "generic"


def normalize_browser_url(url: str, platform: str) -> str:
    if platform == "steam" and "store.steampowered.com" in urlparse(url).netloc.lower():
        match = re.search(r"/app/(\d+)", url)
        if match:
            return f"https://steamcommunity.com/app/{match.group(1)}/reviews/?browsefilter=toprated"
    return url


def emit_result(result: dict, out_path: Path | None, max_chars: int = 0) -> None:
    if max_chars > 0:
        result["reviews"] = [
            (r[:max_chars] + "…") if len(r) > max_chars else r
            for r in result.get("reviews", [])
        ]
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"已抓取 {result['count']} 条内容，保存至: {out_path}")
        return
    if len(payload) > 25000:
        tmp_file = Path(tempfile.gettempdir()) / f"review_detox_{int(time.time())}.json"
        tmp_file.write_text(payload, encoding="utf-8")
        summary = {
            "url": result.get("url"),
            "platform": result.get("platform"),
            "title": result.get("title"),
            "extraction_mode": result.get("extraction_mode"),
            "warning": result.get("warning"),
            "count": result.get("count"),
            "saved_to": str(tmp_file),
            "note": "完整 JSON 超过 25KB，已自动落盘避免终端截断，请直接读取 saved_to 文件。",
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(payload)


def clean_review_text(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return ""
    cleaned = re.split(r"(?:商家回复|掌柜回复|官方回复|店家回复)[:：]", cleaned, maxsplit=1)[0].strip()
    if not cleaned:
        return ""
    if re.match(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?(\s+\d{1,2}:\d{2})?$", cleaned):
        return ""
    return cleaned


def fetch_steam_api(url: str, num_per_page: int = 50) -> dict | None:
    match = re.search(r"/app/(\d+)", url)
    if not match:
        return None
    appid = match.group(1)
    errors: list[str] = []

    for lang in ("schinese", "all"):
        api_url = (
            f"https://store.steampowered.com/appreviews/{appid}"
            f"?json=1&language={lang}&purchase_type=all&num_per_page={num_per_page}"
        )
        try:
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                final_url = getattr(resp, "url", api_url)
                raw = resp.read().decode("utf-8", errors="replace")
            if not raw.lstrip().startswith("{"):
                errors.append(
                    f"{lang}: 返回了网页而非 JSON（可能触发地区限制或被重定向至 {final_url}）"
                )
                continue
            data = json.loads(raw)
        except Exception as exc:
            errors.append(f"{lang}: 请求异常（{exc}）")
            continue

        reviews = []
        for item in data.get("reviews", []):
            text = clean_review_text(item.get("review") or "")
            if text:
                vote = "推荐" if item.get("voted_up") else "不推荐"
                hours = round((item.get("author", {}).get("playtime_forever", 0) or 0) / 60, 1)
                reviews.append(f"[{vote} | 游玩 {hours}h] {text}")
        if reviews:
            return {
                "url": url,
                "platform": f"steam_api ({lang})",
                "title": f"Steam App {appid}",
                "extraction_mode": "api",
                "warning": None,
                "count": len(reviews),
                "reviews": reviews,
            }

    if errors:
        raise RuntimeError("；".join(errors))
    return None


def try_click_tab(page, labels: list[str]) -> bool:
    for label in labels:
        try:
            locator = page.get_by_text(label, exact=False).first
            if locator.is_visible(timeout=800):
                locator.click(timeout=1500)
                time.sleep(1.2)
                return True
        except Exception:
            continue
    return False


def collect_from_selectors(
    page,
    selectors: list[str],
    collected: list[str],
    seen: set[str],
    prefix: str = "",
) -> None:
    for sel in selectors:
        try:
            items = page.locator(sel).all_inner_texts()
            for text in items:
                cleaned = clean_review_text(text)
                if len(cleaned) >= 6 and cleaned not in seen:
                    seen.add(cleaned)
                    collected.append(f"{prefix}{cleaned}" if prefix else cleaned)
        except Exception:
            continue


def collect_steam_cards(page, collected: list[str], seen: set[str]) -> None:
    try:
        cards = page.locator(".apphub_CardContentMain, .review_box")
        count = cards.count()
        for idx in range(count):
            card = cards.nth(idx)
            content_loc = card.locator(".apphub_CardTextContent, .content").first
            if content_loc.count() == 0:
                continue
            body = clean_review_text(content_loc.inner_text(timeout=500))
            body = re.sub(r"^发布于[:：]?\s*(?:\d{4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日\s*", "", body).strip()
            if len(body) < 2:
                continue
            title_txt = ""
            hours_txt = ""
            if card.locator(".title").count() > 0:
                title_txt = clean_review_text(card.locator(".title").first.inner_text(timeout=500))
            if card.locator(".hours").count() > 0:
                hours_txt = clean_review_text(card.locator(".hours").first.inner_text(timeout=500))
            meta = " | ".join(part for part in (title_txt, hours_txt) if part)
            entry = f"[{meta}] {body}" if meta else body
            if entry not in seen:
                seen.add(entry)
                collected.append(entry)
    except Exception:
        pass


def collect_taobao_cards(page, collected: list[str], seen: set[str], prefix: str = "") -> None:
    try:
        cards = page.locator("[class*='Comment--item'], [class*='commentCard'], .tb-revbd li, [class*='rate-grid'] tr")
        count = cards.count()
        for idx in range(count):
            card = cards.nth(idx)
            content_loc = card.locator("[class*='Comment--content'], [class*='commentContent'], [class*='content--'], .tm-rate-fulltxt").first
            if content_loc.count() == 0:
                continue
            body = clean_review_text(content_loc.inner_text(timeout=500))
            if len(body) < 4:
                continue
            meta_txt = ""
            meta_loc = card.locator("[class*='meta'], [class*='sku'], [class*='date'], [class*='info'], .tm-rate-date, .tb-r-info").first
            if meta_loc.count() > 0:
                meta_txt = clean_review_text(meta_loc.inner_text(timeout=500))
            append_txt = ""
            append_loc = card.locator("[class*='append'], [class*='Append'], .tm-rate-append").first
            if append_loc.count() > 0:
                append_txt = clean_review_text(append_loc.inner_text(timeout=500))
            entry = f"[{meta_txt}] {body}" if meta_txt else body
            if append_txt and append_txt != body:
                entry = f"{entry} | [追评] {append_txt}"
            if prefix:
                entry = f"{prefix}{entry}"
            if entry not in seen:
                seen.add(entry)
                collected.append(entry)
    except Exception:
        pass


def scroll_and_collect(page, platform: str, max_scrolls: int = 8, sample_negative: bool = True) -> tuple[list[str], str]:
    selectors = PLATFORM_SELECTORS.get(platform, [])
    collected: list[str] = []
    seen: set[str] = set()

    for _ in range(max_scrolls):
        page.mouse.wheel(0, 1400)
        time.sleep(1.0)
        if platform == "steam":
            collect_steam_cards(page, collected, seen)
        elif platform == "taobao":
            collect_taobao_cards(page, collected, seen)
        if not collected or platform not in ("steam", "taobao"):
            collect_from_selectors(page, selectors, collected, seen)

    if sample_negative and selectors:
        for tab in FILTER_REVIEW_TABS:
            if try_click_tab(page, [tab]):
                for _ in range(3):
                    page.mouse.wheel(0, 1200)
                    time.sleep(0.9)
                    collect_from_selectors(page, selectors, collected, seen, prefix=f"[{tab}] ")

    if collected:
        return collected, "selector"

    body_text = page.locator("body").inner_text(timeout=5000)
    for line in body_text.splitlines():
        cleaned = clean_review_text(line)
        if len(cleaned) >= 12 and cleaned not in seen:
            seen.add(cleaned)
            collected.append(cleaned)

    return collected, "body_fallback"


def detect_warning(title: str, reviews: list[str], extraction_mode: str, platform: str = "generic") -> str | None:
    hit_title = next((kw for kw in LOGIN_WALL_KEYWORDS if kw in title), None)
    if hit_title:
        return f"检测到页面标题疑似触发登录墙或风控（命中：{hit_title}），抓取内容可能无效，建议用 --login 重新登录或改用书签提取。"
    if extraction_mode == "body_fallback" or len(reviews) <= 8:
        joined = " ".join(reviews[:5])
        hit_body = next((kw for kw in LOGIN_WALL_KEYWORDS if kw in joined), None)
        if hit_body:
            return f"检测到页面可能触发登录墙或风控（命中：{hit_body}），抓取内容可能无效，建议用 --login 重新登录或改用书签提取。"
    if extraction_mode == "body_fallback":
        if platform == "taobao":
            return "天猫/淘宝新版评论抽屉选择器未命中，当前仅抓到页面默认展示区（可能偏重追评或混入店铺/SKU杂项，请按订单日期行归并后分析）。"
        return "未匹配到专属评论区选择器，已启用正文兜底提取（可能混入导航栏或推荐商品文字）。"
    return None


def launch_profile_context(playwright, preferred_channel: str | None, headless: bool, profile_dir: Path):
    profile_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[str | None] = []
    for ch in (preferred_channel, "chrome", "msedge", None):
        if ch not in candidates:
            candidates.append(ch)

    last_err: Exception | None = None
    for ch in candidates:
        kwargs = {
            "user_data_dir": str(profile_dir),
            "headless": headless,
            "viewport": {"width": 1280, "height": 860},
        }
        if ch is not None:
            kwargs["channel"] = ch
        try:
            return playwright.chromium.launch_persistent_context(**kwargs)
        except Exception as exc:
            last_err = exc
            continue

    raise RuntimeError(
        f"无法启动本地 Chrome/Edge 或内置 Chromium（最后错误：{last_err}）。"
        "请运行 `playwright install chromium`，或改用 bookmarklet/extract_reviews.js 零安装书签提取。"
    )


def wait_for_manual_login(page, wait_seconds: int) -> None:
    print(
        "请在弹出的浏览器窗口中完成登录或滑块验证（部分平台为页面内浮层弹窗，URL 不会跳转属正常现象）。",
        flush=True,
    )
    if sys.stdin.isatty():
        input("完成登录后，请回到本终端按 Enter 键继续抓取...")
        return

    print(
        f"当前为非交互终端，请在 {wait_seconds} 秒内完成登录，等待倒计时结束将自动继续（若提前关闭窗口，重新运行不加 --login 的命令即可）...",
        flush=True,
    )
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if page.is_closed():
            break
        time.sleep(1.5)


def main() -> None:
    configure_stdio()

    parser = argparse.ArgumentParser(description="复用本地浏览器登录态抓取网页评论区")
    parser.add_argument("url", help="商品/软件/帖子链接")
    parser.add_argument(
        "--mode",
        choices=["profile", "cdp"],
        default="profile",
        help="profile: 复用本地持久化登录目录; cdp: 连接已开启调试端口的浏览器",
    )
    parser.add_argument("--port", type=int, default=9222, help="CDP 模式调试端口号（默认 9222）")
    parser.add_argument(
        "--channel",
        default="msedge",
        choices=["msedge", "chrome", "chromium"],
        help="优先尝试的本地浏览器内核（默认 msedge，失败会自动尝试 chrome/chromium）",
    )
    parser.add_argument("--login", action="store_true", help="打开可见窗口等待手动登录/过验证码")
    parser.add_argument("--login-wait", type=int, default=90, help="非交互终端下 --login 最长等待秒数（默认 90）")
    parser.add_argument("--headed", action="store_true", help="强制使用有头可见浏览器窗口")
    parser.add_argument("--headless", action="store_true", help="强制使用无头模式")
    parser.add_argument("--scrolls", type=int, default=8, help="向下滚动加载评论次数（默认 8）")
    parser.add_argument("--no-diff", action="store_true", help="跳过追评/中评/差评补充采样")
    parser.add_argument("--max-chars", type=int, default=0, help="可选：单条评论最大字符数限制（0 表示不截断）")
    parser.add_argument("--out", type=Path, default=None, help="可选：将抓取结果保存为 JSON 文件")
    args = parser.parse_args()

    platform = detect_platform(args.url)

    if platform == "steam" and not args.login:
        try:
            result = fetch_steam_api(args.url)
            if result and result["count"] > 0:
                emit_result(result, args.out, max_chars=args.max_chars)
                return
            print("Steam 公开接口未返回评价（可能该游戏锁区或需登录态），尝试切换浏览器模式...", file=sys.stderr)
        except Exception as exc:
            print(f"Steam 公开接口直连失败（{exc}），尝试切换浏览器模式...", file=sys.stderr)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "当前链接需要浏览器渲染或登录态，请先安装 playwright（pip install playwright），"
            "或使用 bookmarklet/extract_reviews.js 零安装书签提取后直接粘贴评论。",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.login or args.headed:
        headless = False
    elif args.headless:
        headless = True
    else:
        headless = platform not in ECOMMERCE_PLATFORMS

    preferred_channel = None if args.channel == "chromium" else args.channel

    with sync_playwright() as p:
        if args.mode == "cdp":
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            should_close_context = False
        else:
            context = launch_profile_context(
                p,
                preferred_channel=preferred_channel,
                headless=headless,
                profile_dir=DEFAULT_PROFILE_DIR,
            )
            page = context.pages[0] if context.pages else context.new_page()
            should_close_context = True

        target_url = normalize_browser_url(args.url, platform)
        if target_url != args.url:
            print(f"已自动切换至 Steam 社区评测页以避开商店页噪音: {target_url}", file=sys.stderr)
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2.0)

            if args.login:
                wait_for_manual_login(page, args.login_wait)
                if page.is_closed():
                    try:
                        page = context.new_page()
                        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                        time.sleep(2.0)
                    except Exception:
                        print("登录态已保存，请重新运行脚本（不加 --login）开始抓取。")
                        return

            try_click_tab(page, PRIMARY_REVIEW_TABS)
            reviews, extraction_mode = scroll_and_collect(
                page,
                platform,
                max_scrolls=args.scrolls,
                sample_negative=not args.no_diff,
            )
            title = page.title()
            warning = detect_warning(title, reviews, extraction_mode, platform=platform)

            result = {
                "url": args.url,
                "platform": platform,
                "title": title,
                "extraction_mode": extraction_mode,
                "warning": warning,
                "count": len(reviews),
                "reviews": reviews,
            }

            if warning:
                print(f"[警告] {warning}", file=sys.stderr)

            emit_result(result, args.out, max_chars=args.max_chars)
        finally:
            try:
                if args.mode == "cdp":
                    page.close()
                elif should_close_context:
                    context.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
