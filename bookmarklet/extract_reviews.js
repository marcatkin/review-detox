(function () {
  const host = location.hostname.toLowerCase();
  const isSteam = host.includes("steampowered.com") || host.includes("steamcommunity.com");
  const isTaobao = host.includes("taobao.com") || host.includes("tmall.com");
  let selectors = [];

  if (host.includes("taobao.com") || host.includes("tmall.com")) {
    selectors = [
      "[class*='Comment--content']",
      "[class*='commentContent']",
      "[class*='Comment--item']",
      "[class*='commentCard']",
      "[class*='Comments--'] [class*='content--']",
      "[class*='rate-grid'] td.tm-col-master",
      ".tb-revbd li",
      "[class*='review'] [class*='content']"
    ];
  } else if (host.includes("jd.com")) {
    selectors = [
      ".comment-item .comment-con",
      ".comment-column .comment-con",
      "[class*='comment-con']"
    ];
  } else if (host.includes("xiaohongshu.com")) {
    selectors = [
      ".comment-item .content",
      "[class*='note-text']",
      "[class*='comment'] [class*='content']"
    ];
  } else if (isSteam) {
    selectors = [".apphub_CardTextContent", ".review_box .content"];
  } else if (host.includes("douban.com")) {
    selectors = [".comment-item .short", ".review-short .short-content"];
  }

  function cleanText(raw) {
    const txt = (raw || "").replace(/\s+/g, " ").trim();
    if (!txt) return "";
    const cut = txt.split(/(?:商家回复|掌柜回复|官方回复|店家回复)[:：]/)[0].trim();
    return cut;
  }

  const seen = new Set();
  const items = [];

  if (isSteam) {
    const cards = document.querySelectorAll(".apphub_CardContentMain, .review_box");
    cards.forEach((card) => {
      const titleEl = card.querySelector(".title");
      const hoursEl = card.querySelector(".hours");
      const contentEl = card.querySelector(".apphub_CardTextContent, .content");
      if (!contentEl) return;
      const body = cleanText(contentEl.innerText).replace(/^发布于[:：]?\s*(?:\d{4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日\s*/, "").trim();
      if (body.length < 2) return;
      const meta = [cleanText(titleEl && titleEl.innerText), cleanText(hoursEl && hoursEl.innerText)].filter(Boolean).join(" | ");
      const full = meta ? `[${meta}] ${body}` : body;
      if (!seen.has(full)) {
        seen.add(full);
        items.push(full);
      }
    });
  }

  if (isTaobao) {
    const cards = document.querySelectorAll("[class*='Comment--item'], [class*='commentCard'], .tb-revbd li, [class*='rate-grid'] tr");
    cards.forEach((card) => {
      const contentEl = card.querySelector("[class*='Comment--content'], [class*='commentContent'], [class*='content--'], .tm-rate-fulltxt");
      const body = cleanText(contentEl ? contentEl.innerText : "");
      if (body.length < 4) return;
      const metaEl = card.querySelector("[class*='meta'], [class*='sku'], [class*='date'], [class*='info'], .tm-rate-date, .tb-r-info");
      const meta = cleanText(metaEl ? metaEl.innerText : "");
      const appendEl = card.querySelector("[class*='append'], [class*='Append'], .tm-rate-append");
      const appendTxt = cleanText(appendEl ? appendEl.innerText : "");
      let full = meta ? `[${meta}] ${body}` : body;
      if (appendTxt && appendTxt !== body) {
        full += ` | [追评] ${appendTxt}`;
      }
      if (!seen.has(full)) {
        seen.add(full);
        items.push(full);
      }
    });
  }


  if (items.length === 0) {
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => {
        const txt = cleanText(el.innerText);
        if (txt.length >= 6 && !seen.has(txt)) {
          seen.add(txt);
          items.push(txt);
        }
      });
    }
  }

  let usedFallback = false;
  if (items.length === 0) {
    usedFallback = true;
    (document.body.innerText || "").split(/\n+/).forEach((line) => {
      const txt = cleanText(line);
      if (txt.length >= 15 && !seen.has(txt)) {
        seen.add(txt);
        items.push(txt);
      }
    });
  }

  if (items.length === 0) {
    alert("当前页面未检测到评论内容，请先点击展开评论区或向下滚动几屏后再试。");
    return;
  }

  const modeHint = usedFallback
    ? "未识别到专属评论区，已启用全文兜底（可能含页面杂项）"
    : "已通过专属规则精准提取";

  const output = [
    `来源标题：${document.title}`,
    `来源链接：${location.href}`,
    `提取模式：${usedFallback ? "全文兜底" : "精准选择器"}`,
    `提取条数：${items.length}`,
    "---",
    ...items.map((t, i) => `${i + 1}. ${t}`)
  ].join("\n");

  function showManualCopyModal(text, count) {
    const overlay = document.createElement("div");
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:2147483647;display:flex;align-items:center;justify-content:center;padding:20px;";
    const box = document.createElement("div");
    box.style.cssText =
      "background:#fff;color:#111;border-radius:10px;padding:16px;width:min(720px,95vw);max-height:85vh;display:flex;flex-direction:column;gap:10px;font-family:sans-serif;";
    const title = document.createElement("div");
    title.style.cssText = "font-weight:bold;font-size:15px;";
    title.textContent = `${modeHint} ${count} 条内容，请全选复制（Ctrl+A 后 Ctrl+C）后关闭：`;
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "width:100%;height:340px;font-size:12px;padding:8px;box-sizing:border-box;";
    const btn = document.createElement("button");
    btn.textContent = "关闭";
    btn.style.cssText = "align-self:flex-end;padding:6px 16px;cursor:pointer;";
    btn.onclick = () => overlay.remove();
    box.append(title, ta, btn);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    ta.focus();
    ta.select();
  }

  function legacyCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;left:-9999px;top:0;";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (e) {
      ok = false;
    }
    ta.remove();
    return ok;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(output)
      .then(() => {
        alert(usedFallback ? `⚠️ 未识别到当前页面的评论区，已启用全文兜底（共 ${items.length} 行，可能仅包含推荐列表/导航杂项而非真实评论）。已复制到剪贴板，请先核对再粘贴给 AI！` : `已通过专属规则精准提取 ${items.length} 条评论并复制到剪贴板！直接粘贴给 AI 即可。`);
      })
      .catch(() => {
        if (legacyCopy(output)) {
          alert(usedFallback ? `⚠️ 未识别到当前页面的评论区，已启用全文兜底（共 ${items.length} 行，可能仅包含推荐列表/导航杂项而非真实评论）。已复制到剪贴板，请先核对再粘贴给 AI！` : `已通过专属规则精准提取 ${items.length} 条评论并复制到剪贴板！直接粘贴给 AI 即可。`);
        } else {
          showManualCopyModal(output, items.length);
        }
      });
  } else if (legacyCopy(output)) {
    alert(usedFallback ? `⚠️ 未识别到当前页面的评论区，已启用全文兜底（共 ${items.length} 行，可能仅包含推荐列表/导航杂项而非真实评论）。已复制到剪贴板，请先核对再粘贴给 AI！` : `已通过专属规则精准提取 ${items.length} 条评论并复制到剪贴板！直接粘贴给 AI 即可。`);
  } else {
    showManualCopyModal(output, items.length);
  }
})();
