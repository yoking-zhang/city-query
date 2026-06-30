const input = document.getElementById("searchInput");
const resultEl = document.getElementById("result");
const hintEl = document.getElementById("hint");

input.addEventListener("input", () => {
    const q = input.value.replace(/\s/g, "").toUpperCase();

    if (q.length === 0) {
        hintEl.textContent = "支持: 身份证前缀 | 区号 | 邮编 | 车牌 | 省/市/县名称";
        hintEl.style.color = "";
    } else {
        hintEl.textContent = "按 Enter 键查询";
        hintEl.style.color = "var(--color-primary)";
    }
});

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        const q = input.value.replace(/\s/g, "").toUpperCase();
        if (q.length > 0) {
            doSearch(q);
        }
    }
});

async function doSearch(q) {
    resultEl.innerHTML = '<div class="result-card"><p style="text-align:center;color:var(--color-text-muted);">查询中...</p></div>';

    try {
        const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await resp.json();

        if (data.error) {
            resultEl.innerHTML = `<div class="result-error">⚠️ ${escapeHtml(data.error)}</div>`;
            return;
        }

        renderResults(data.results, q);
    } catch (err) {
        resultEl.innerHTML = `<div class="result-error">⚠️ 网络错误: ${escapeHtml(err.message)}</div>`;
    }
}

function renderResults(results, prefix) {
    if (!results || results.length === 0) {
        resultEl.innerHTML = `<div class="result-error">未找到前缀为「${escapeHtml(prefix)}」的区域信息</div>`;
        return;
    }

    const cards = results.map(r => buildCard(r, prefix)).join("");
    resultEl.innerHTML = `<div class="result-list">${cards}</div>`;
}

function buildCard(r, inputPrefix) {
    const len = r.prefix.length;
    let locationHtml = "";
    let childrenHtml = "";

    if (!r.city) {
        // 省份：面包屑 + 城市列表
        locationHtml = `<span class="name province">${escapeHtml(r.province)}</span>`;
        if (r.children && r.children.length > 0) {
            childrenHtml = buildChildrenTable(r.children, "城市", "city", true);
        }
    } else if (!r.district) {
        // 省市：面包屑省份可点击回跳 + 区县列表
        locationHtml = `
            <span class="name province clickable" data-prefix="${escapeHtml(r.prefix2)}" title="点击查询 ${escapeHtml(r.province)}">${escapeHtml(r.province)}</span>
            <span class="sep">›</span>
            <span class="name city">${escapeHtml(r.city)}</span>`;
        if (r.children && r.children.length > 0) {
            childrenHtml = buildChildrenTable(r.children, "区县", "district");
        }
    } else {
        // 省市县：面包屑，省市可点击回跳
        locationHtml = `
            <span class="name province clickable" data-prefix="${escapeHtml(r.prefix2)}" title="点击查询 ${escapeHtml(r.province)}">${escapeHtml(r.province)}</span>
            <span class="sep">›</span>
            <span class="name city clickable" data-prefix="${escapeHtml(r.prefix4)}" title="点击查询 ${escapeHtml(r.city)}">${escapeHtml(r.city)}</span>
            <span class="sep">›</span>
            <span class="name district">${escapeHtml(r.district)}</span>`;
    }

    // 区号/邮编/车牌 附加信息
    let extraHtml = "";
    let parts = [];
    if (r.areacode) parts.push(`<div class="extra-row">📞 区号: ${escapeHtml(r.areacode)}</div>`);
    if (r.postcode) parts.push(`<div class="extra-row">📮 邮编: ${escapeHtml(r.postcode)}</div>`);
    if (r.car_prefix) parts.push(`<div class="extra-row">🚗 车牌: ${escapeHtml(r.car_prefix)}</div>`);
    if (parts.length > 0) {
        extraHtml = `<div class="extra-info">${parts.join("")}</div>`;
    }

    return `
        <div class="result-card">
            <div class="prefix-badge">${escapeHtml(r.prefix)}</div>
            <div class="location">${locationHtml}</div>
            ${extraHtml}
            <div class="adcode">🏷️ 行政区划代码: ${escapeHtml(r.adcode)}</div>
            ${childrenHtml}
        </div>`;
}

function buildChildrenTable(children, label, levelClass, showCarPrefix = false) {
    let items = children.map(c => `
        <div class="child-item" data-prefix="${escapeHtml(c.prefix)}" title="点击查询 ${escapeHtml(c.name)}">
            <span class="child-prefix">${escapeHtml(c.prefix)}</span>
            <span class="child-name ${levelClass}">${escapeHtml(c.name)}</span>
            ${showCarPrefix ? `<span class="child-car">${escapeHtml(c.car_prefix || '—')}</span>` : ''}
        </div>
    `).join("");

    return `
        <div class="children-section">
            <div class="children-header">${label}列表（${children.length} 个，点击可跳转查询）</div>
            <div class="children-grid">${items}</div>
        </div>`;
}

// 事件委托：点击子节点行 or 面包屑可点击元素触发查询
document.getElementById("result").addEventListener("click", (e) => {
    const target = e.target.closest(".child-item, .clickable");
    if (!target) return;

    const prefix = target.dataset.prefix;
    if (prefix) {
        input.value = prefix;
        input.focus();
        doSearch(prefix);
        window.scrollTo({ top: 0, behavior: "smooth" });
    }
});

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
