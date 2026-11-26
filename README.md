# 🧼 Review Detox — 评论区“去水军 / 避坑”提炼器

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)
![Agent Skill](https://img.shields.io/badge/Agent-Skill-purple.svg)

> **把充斥刷单好评和返现话术的评论区，清洗成一份“客观六维打分 + 按真实比例列优缺点 + 明确适用/劝退人群”的硬核避坑测评。**

## 🧭 10 秒看懂你该怎么用

| 你的使用场景 | 推荐方式 | 需要装软件吗？ |
| :--- | :--- | :--- |
| **用网页版 AI**（ChatGPT / Claude / DeepSeek 网页端），逛淘宝/京东/小红书 | **方式 A（书签一键提取）** | **零安装**，鼠标拖一下书签即可 |
| **用本地 AI Agent**（Codex / Claude Code / Cursor），想测 **Steam** 游戏 | **方式 B（给链接直抓）** | **零第三方依赖**（仅需 Python 3.9+） |
| **用本地 AI Agent**，想给链接全自动抓 **淘宝 / 京东 / 小红书** | **方式 B（本地浏览器复用）** | 需 `pip install playwright`（复用本地 Chrome/Edge） |

---

## 🚀 快速上手

### 方式 A：零安装 · 浏览器书签一键提取（最推荐）

1. **一拖安装**：直接用浏览器打开本仓库的 `bookmarklet/install.html`，把里面的蓝色按钮拖到浏览器书签栏。
2. **或者手动新建书签**：复制下面这一整行代码，粘贴进浏览器新书签的**网址（URL）**栏：
   ```text
   javascript:(function () { const host = location.hostname.toLowerCase(); const isSteam = host.includes("steampowered.com") || host.includes("steamcommunity.com"); const isTaobao = host.includes("taobao.com") || host.includes("tmall.com"); let selectors = []; if (host.includes("taobao.com") || host.includes("tmall.com")) { selectors = [ "[class*='Comment--content']", "[class*='commentContent']", "[class*='Comment--item']", "[class*='commentCard']", "[class*='Comments--'] [class*='content--']", "[class*='rate-grid'] td.tm-col-master", ".tb-revbd li", "[class*='review'] [class*='content']" ]; } else if (host.includes("jd.com")) { selectors = [ ".comment-item .comment-con", ".comment-column .comment-con", "[class*='comment-con']" ]; } else if (host.includes("xiaohongshu.com")) { selectors = [ ".comment-item .content", "[class*='note-text']", "[class*='comment'] [class*='content']" ]; } else if (isSteam) { selectors = [".apphub_CardTextContent", ".review_box .content"]; } else if (host.includes("douban.com")) { selectors = [".comment-item .short", ".review-short .short-content"]; } function cleanText(raw) { const txt = (raw || "").replace(/\s+/g, " ").trim(); if (!txt) return ""; const cut = txt.split(/(?:商家回复|掌柜回复|官方回复|店家回复)[:：]/)[0].trim(); return cut; } const seen = new Set(); const items = []; if (isSteam) { const cards = document.querySelectorAll(".apphub_CardContentMain, .review_box"); cards.forEach((card) => { const titleEl = card.querySelector(".title"); const hoursEl = card.querySelector(".hours"); const contentEl = card.querySelector(".apphub_CardTextContent, .content"); if (!contentEl) return; const body = cleanText(contentEl.innerText).replace(/^发布于[:：]?\s*(?:\d{4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日\s*/, "").trim(); if (body.length < 2) return; const meta = [cleanText(titleEl && titleEl.innerText), cleanText(hoursEl && hoursEl.innerText)].filter(Boolean).join(" | "); const full = meta ? `[${meta}] ${body}` : body; if (!seen.has(full)) { seen.add(full); items.push(full); } }); } if (isTaobao) { const cards = document.querySelectorAll("[class*='Comment--item'], [class*='commentCard'], .tb-revbd li, [class*='rate-grid'] tr"); cards.forEach((card) => { const contentEl = card.querySelector("[class*='Comment--content'], [class*='commentContent'], [class*='content--'], .tm-rate-fulltxt"); const body = cleanText(contentEl ? contentEl.innerText : ""); if (body.length < 4) return; const metaEl = card.querySelector("[class*='meta'], [class*='sku'], [class*='date'], [class*='info'], .tm-rate-date, .tb-r-info"); const meta = cleanText(metaEl ? metaEl.innerText : ""); const appendEl = card.querySelector("[class*='append'], [class*='Append'], .tm-rate-append"); const appendTxt = cleanText(appendEl ? appendEl.innerText : ""); let full = meta ? `[${meta}] ${body}` : body; if (appendTxt && appendTxt !== body) { full += ` | [追评] ${appendTxt}`; } if (!seen.has(full)) { seen.add(full); items.push(full); } }); } if (items.length === 0) { for (const sel of selectors) { document.querySelectorAll(sel).forEach((el) => { const txt = cleanText(el.innerText); if (txt.length >= 6 && !seen.has(txt)) { seen.add(txt); items.push(txt); } }); } } let usedFallback = false; if (items.length === 0) { usedFallback = true; (document.body.innerText || "").split(/\n+/).forEach((line) => { const txt = cleanText(line); if (txt.length >= 15 && !seen.has(txt)) { seen.add(txt); items.push(txt); } }); } if (items.length === 0) { alert("当前页面未检测到评论内容，请先点击展开评论区或向下滚动几屏后再试。"); return; } const modeHint = usedFallback ? "未识别到专属评论区，已启用全文兜底（可能含页面杂项）" : "已通过专属规则精准提取"; const output = [ `来源标题：${document.title}`, `来源链接：${location.href}`, `提取模式：${usedFallback ? "全文兜底" : "精准选择器"}`, `提取条数：${items.length}`, "---", ...items.map((t, i) => `${i + 1}. ${t}`) ].join("\n"); function showManualCopyModal(text, count) { const overlay = document.createElement("div"); overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:2147483647;display:flex;align-items:center;justify-content:center;padding:20px;"; const box = document.createElement("div"); box.style.cssText = "background:#fff;color:#111;border-radius:10px;padding:16px;width:min(720px,95vw);max-height:85vh;display:flex;flex-direction:column;gap:10px;font-family:sans-serif;"; const title = document.createElement("div"); title.style.cssText = "font-weight:bold;font-size:15px;"; title.textContent = `${modeHint} ${count} 条内容，请全选复制（Ctrl+A 后 Ctrl+C）后关闭：`; const ta = document.createElement("textarea"); ta.value = text; ta.style.cssText = "width:100%;height:340px;font-size:12px;padding:8px;box-sizing:border-box;"; const btn = document.createElement("button"); btn.textContent = "关闭"; btn.style.cssText = "align-self:flex-end;padding:6px 16px;cursor:pointer;"; btn.onclick = () => overlay.remove(); box.append(title, ta, btn); overlay.appendChild(box); document.body.appendChild(overlay); ta.focus(); ta.select(); } function legacyCopy(text) { const ta = document.createElement("textarea"); ta.value = text; ta.style.cssText = "position:fixed;left:-9999px;top:0;"; document.body.appendChild(ta); ta.focus(); ta.select(); let ok = false; try { ok = document.execCommand("copy"); } catch (e) { ok = false; } ta.remove(); return ok; } if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard .writeText(output) .then(() => { alert(usedFallback ? `⚠️ 未识别到当前页面的评论区，已启用全文兜底（共 ${items.length} 行，可能仅包含推荐列表/导航杂项而非真实评论）。已复制到剪贴板，请先核对再粘贴给 AI！` : `已通过专属规则精准提取 ${items.length} 条评论并复制到剪贴板！直接粘贴给 AI 即可。`); }) .catch(() => { if (legacyCopy(output)) { alert(usedFallback ? `⚠️ 未识别到当前页面的评论区，已启用全文兜底（共 ${items.length} 行，可能仅包含推荐列表/导航杂项而非真实评论）。已复制到剪贴板，请先核对再粘贴给 AI！` : `已通过专属规则精准提取 ${items.length} 条评论并复制到剪贴板！直接粘贴给 AI 即可。`); } else { showManualCopyModal(output, items.length); } }); } else if (legacyCopy(output)) { alert(usedFallback ? `⚠️ 未识别到当前页面的评论区，已启用全文兜底（共 ${items.length} 行，可能仅包含推荐列表/导航杂项而非真实评论）。已复制到剪贴板，请先核对再粘贴给 AI！` : `已通过专属规则精准提取 ${items.length} 条评论并复制到剪贴板！直接粘贴给 AI 即可。`); } else { showManualCopyModal(output, items.length); } })();
   ```
3. **提取并出报告**：在商品页点开评论区并滑几屏，点一下书签即可自动去重复制评论；贴给任意 AI（把 `SKILL.md` 内容作为前置指令）即可出报告。

### 方式 B：给链接全自动抓取（适用于 Codex / Claude Code / Cursor）

> 提示：给链接全自动运行脚本仅适用于**支持本地执行命令的 AI Agent**；网页版聊天框请直接使用方式 A。

1. **安装依赖**（Python 3.9+；若只测 Steam 公开接口可跳过此步）：
   ```bash
   python -m pip install -r requirements.txt
   ```
   > 多 Python 版本提醒：请确保安装依赖和运行脚本使用同一个 Python 解释器（或直接用 `uv run --with playwright python scripts/fetch_reviews.py "<链接>"` 免环境冲突）。
   > 默认自动检测本地已安装的 Chrome / Edge；若全未安装，可运行 `playwright install chromium` 下载内置内核。
2. **首次登录保存本地登录态**（淘宝/京东/小红书只需扫码一次，登录态保存在用户主目录 `~/.review-detox/browser_profile`，**与代码仓库物理隔离**，不会随代码提交泄露）：
   ```bash
   python scripts/fetch_reviews.py "https://detail.tmall.com/item.htm?id=<商品ID>" --login
   ```
   在弹出的浏览器窗口里完成扫码或滑块后，回到终端按 `Enter` 键继续。
3. **直接给链接出报告**：把整个 `review-detox` 文件夹放到 `~/.codex/skills/` 或 `~/.agents/skills/`，在对话里直接说：
   > **“用 review-detox 测一下这个链接：`https://...`，我最在意售后和质量。”**

<details>
<summary>进阶：通过 CDP 调试端口直连现有浏览器（含新版 Chrome 限制与安全提醒）</summary>

- **安全提醒**：开启远程调试端口会暴露该浏览器实例中的全部登录态给本机任意进程，请勿在主力日常浏览器长期开启，用完即关。
- **新版 Chrome / Edge（136+）限制**：必须配合非默认 `--user-data-dir` 才能开启调试端口，例如：
  ```bash
  msedge.exe --remote-debugging-port=9222 --user-data-dir="C:\temp\edge-debug"
  ```
- 启动并登录目标平台后，使用 `--mode cdp --port 9222` 运行抓取脚本即可。

</details>

---

## 📊 报告长什么样？（完整脱敏示例）

<details>
<summary>点击展开：真实天猫无线机械键盘 59 条评论去水军测评输出示例</summary>

```markdown
# 【避坑体检】某百元档无线三模机械键盘 —— 手感与颜值能打，但品控抽奖和一个月后的“掉漆/失灵/售后推诿”必须警惕
**避坑评级：B（能用但挑人）** | **水军与模板浓度：平台折叠 101 条低质评价；可见 59 条中约 20%（12 条）为无细节模板好评，有效样本 47 条**

## 固定六维评价
| 评价维度 | 评分 | 一句话定性 |
| :--- | :--- | :--- |
| **1. 性价比 / 价格** | ★★★★☆ (4.5) | 百亿补贴 ¥150 档给到全键热插拔与彩屏旋钮，硬件配置高 |
| **2. 质量 / 做工品控** | ★★☆☆☆ (2.5) | 存在明显批次品控抽奖（坏轴、涂层掉漆、脚架脱落） |
| **3. 核心体验 / 性能** | ★★★★☆ (4.0) | 2.4G/有线敲击手感与声音稳，但蓝牙稳定性较差 |
| **4. 使用门槛 / 易用性** | ★★★☆☆ (3.0) | 非静音轴体宿舍慎用；暗处键帽不透光 |
| **5. 售后服务 / 退换体验** | ★★☆☆☆ (2.0) | 7 天无理由顺畅，过 7 天后出现质量问题存在推诿 |
| **6. 长期口碑 / 追评表现** | ★★☆☆☆ (2.5) | 21 天～160 天深度追评集中暴露耐用度短板 |

## 核心优点与缺点（统一以 47 条有效样本为分母）
### 核心优点
1. **敲击手感软弹、声音表现好**（有效样本提及 25/47 条，占比 53%）
2. **外观颜值高、配色丰富**（有效样本提及 21/47 条，占比 45%）

### 核心缺点
1. **中长期品控与耐用度翻车（硬件/工艺问题）**（有效样本提及 5/47 条，占比 11%；深度追评中占比较高）
   > 原话：“23天后追评：正常使用一个月键帽白色部分就出现明显掉漆/涂层脱落……”
2. **蓝牙连接不稳定（无线体验短板）**（有效样本提及 2/47 条，占比 4%）
   > 原话：“蓝牙很难连，蓝牙最慢，要快只能用有线的！”

## 〖购买建议〗
- **✅ 适用人群**：预算 150～200 元、固定插 2.4G/有线使用、追求手感与颜值的桌面玩家。
- **❌ 不建议人群**：强依赖多设备蓝牙连接的用户、手汗重买浅色款指望长期不掉漆的群体（建议优先考虑深色 PBT 键帽款式）。
```

</details>

---

## 📁 仓库结构

```text
review-detox/
├── SKILL.md                      # 核心 Skill 指令（触发条件 + 防注入 + 4步测评流程）
├── scripts/
│   └── fetch_reviews.py          # 复用本地浏览器登录态抓取评论区（Steam 免依赖）
├── bookmarklet/
│   ├── extract_reviews.js        # 零安装浏览器书签源码
│   └── install.html              # 小白拖拽安装页
├── references/
│   ├── style-guide.md            # 客观硬核测评排版、六维表与语言禁令规范
│   └── shill-patterns.md         # 各平台水军/刷单/返现话术识别清单
├── requirements.txt
├── .gitignore
├── LICENSE
├── SECURITY.md
└── README.md
```

---

## ⚖️ 免责与合规声明

- **使用范围**：本项目仅供个人学习研究与消费决策参考使用，**严禁用于商业用途、大规模并发采集或任何干扰目标平台正常运营的行为**。
- **技术边界**：本项目不提供验证码破解、不逆向任何平台接口加密签名、不绕过平台访问控制机制；仅复用用户本人的本地浏览器会话读取页面已渲染的公开评价内容。
- **隐私与责任**：项目不收集或上传任何用户 Cookie 与个人隐私数据。使用前请自行阅读并遵守目标网站的服务条款及所在地法律法规，因使用本项目产生的一切风险与责任由使用者自行承担。

## 📄 License

MIT
