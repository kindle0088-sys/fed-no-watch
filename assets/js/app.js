/*!
 * Fed No Watch — Application JS
 * Handles timeline rendering, filtering, search, rate display.
 */

(function() {
  'use strict';

  const app = {};

  // ---- Source display config ----
  const SOURCE_CONFIG = {
    'federal_reserve': { label: 'Federal Reserve', cssClass: 'fed', icon: '🏛' },
    'wallstreetcn':    { label: '华尔街见闻',      cssClass: 'wscn', icon: '📰' },
  };

  const CATEGORY_LABELS = {
    'speech': '演讲',
    'press_release': '新闻稿',
    'fomc': 'FOMC',
    'media_opinion': '新闻/分析',
    'media_speech': '媒体报道',
    'media_fomc': 'FOMC报道',
    'media_rate': '利率分析',
  };

  // ---- DOM refs ----
  let container, loadingEl, emptyState, timelineEl;
  let searchInput, sourceFilter, categoryFilter;
  let liveTimeEl, liveDot;
  let scrollTopBtn;

  // ---- Init ----
  app.init = function() {
    container = document.getElementById('timeline-container');
    if (!container) { return; }

    loadingEl = container.querySelector('.loading');
    emptyState = container.querySelector('.empty-state');
    timelineEl = container.querySelector('.timeline');
    searchInput = document.getElementById('search-input');
    sourceFilter = document.getElementById('source-filter');
    categoryFilter = document.getElementById('category-filter');
    liveTimeEl = document.getElementById('liveTime');
    liveDot = document.getElementById('liveDot');
    scrollTopBtn = document.getElementById('scrollTop');

    // Get data
    const data = typeof SITE_DATA !== 'undefined' ? SITE_DATA : null;
    if (!data || !data.items) {
      if (loadingEl) loadingEl.style.display = 'none';
      if (emptyState) { emptyState.style.display = 'block'; emptyState.innerHTML = '<h3>⚠ 暂无数据</h3><p>数据文件未加载，请检查网络或稍后再试。</p>'; }
      return;
    }

    // Update time/live
    app.updateLiveTime(data);

    // Render
    app.render(data);

    // Filters
    if (searchInput) searchInput.addEventListener('input', () => app.render(data));
    if (sourceFilter) sourceFilter.addEventListener('change', () => app.render(data));
    if (categoryFilter) categoryFilter.addEventListener('change', () => app.render(data));

    // Scroll to top
    if (scrollTopBtn) {
      window.addEventListener('scroll', () => {
        scrollTopBtn.classList.toggle('show', window.scrollY > 300);
      });
      scrollTopBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    }
  };

  // ---- Update Live Bar ----
  app.updateLiveTime = function(data) {
    if (liveTimeEl && data.updated_at) {
      const d = new Date(data.updated_at);
      liveTimeEl.textContent = '更新于 ' + d.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) + ' (北京时间)';
    }
    if (liveDot) {
      liveDot.classList.add('pulse');
    }
  };

  // ---- Filter ----
  app.getFilteredItems = function(data) {
    let items = data.items || [];

    const query = (searchInput?.value || '').toLowerCase().trim();
    const sourceVal = sourceFilter?.value || 'all';
    const catVal = categoryFilter?.value || 'all';

    if (query) {
      items = items.filter(item => {
        return (
          (item.title || '').toLowerCase().includes(query) ||
          (item.summary || '').toLowerCase().includes(query) ||
          (item.speaker || '').toLowerCase().includes(query) ||
          (item.source_label || '').toLowerCase().includes(query)
        );
      });
    }

    if (sourceVal !== 'all') {
      items = items.filter(item => item.source === sourceVal);
    }

    if (catVal !== 'all') {
      items = items.filter(item => item.category === catVal);
    }

    return items;
  };

  // ---- Render Timeline ----
  app.render = function(data) {
    const filtered = app.getFilteredItems(data);

    if (loadingEl) loadingEl.style.display = 'none';
    if (emptyState) emptyState.style.display = 'none';
    if (!timelineEl) return;

    if (filtered.length === 0) {
      timelineEl.innerHTML = '';
      if (emptyState) { emptyState.style.display = 'block'; emptyState.innerHTML = '<h3>🍃 无匹配结果</h3><p>试试修改筛选条件或搜索词。</p>'; }
      return;
    }

    // Group by date for separator
    const groups = {};
    filtered.forEach(item => {
      const d = item.published_at ? app.formatDateShort(item.published_at) : '未知日期';
      if (!groups[d]) groups[d] = [];
      groups[d].push(item);
    });

    let html = '';
    Object.keys(groups).forEach(date => {
      html += `<div class="date-separator">${date}</div>`;
      groups[date].forEach(item => html += app.renderCard(item));
    });

    timelineEl.innerHTML = html;
  };

  // ---- Render Single Card ----
  app.renderCard = function(item) {
    const srcCfg = SOURCE_CONFIG[item.source] || { label: item.source_label || '其他', cssClass: '', icon: '📎' };
    const catLabel = CATEGORY_LABELS[item.category] || item.category || '其他';
    const timeStr = item.published_at ? app.formatTime(item.published_at) : '';

    let extraTags = '';
    if (item.speaker) {
      extraTags += `<span class="extra-tag speaker">🎤 ${app.escapeHtml(item.speaker)}</span>`;
    }

    return `
      <div class="news-card">
        <div class="meta">
          <span class="source-tag ${srcCfg.cssClass}">${srcCfg.icon} ${srcCfg.label}</span>
          <span class="cat-tag">${catLabel}</span>
          <span class="time">${timeStr}</span>
        </div>
        <div class="title">
          <a href="${app.escapeAttr(item.url)}" target="_blank" rel="noopener">${app.escapeHtml(item.title)}</a>
        </div>
        ${item.summary ? `<div class="summary">${app.escapeHtml(item.summary)}</div>` : ''}
        ${extraTags ? `<div class="extra">${extraTags}</div>` : ''}
      </div>
    `;
  };

  // ---- Helpers ----
  app.escapeHtml = function(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  };

  app.escapeAttr = function(str) {
    if (!str) return '#';
    return String(str).replace(/"/g, '&quot;');
  };

  app.formatDateShort = function(isoStr) {
    try {
      const d = new Date(isoStr);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    } catch { return isoStr || ''; }
  };

  app.formatTime = function(isoStr) {
    try {
      const d = new Date(isoStr);
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      return `${month}/${day} ${hh}:${mm}`;
    } catch { return isoStr || ''; }
  };

  // ---- Rate bar update ----
  app.updateRateBar = function(data) {
    const rate = data.fed_rate;
    if (!rate) return;

    const el = document.getElementById('rate-bar-content');
    if (!el) return;

    const targetStr = `${rate.target_lower?.toFixed(2)}% – ${rate.target_upper?.toFixed(2)}%`;
    const effStr = rate.effective_rate?.toFixed(2) + '%';

    let fomcHTML = '';
    if (rate.fomc_dates && rate.fomc_dates.length) {
      const next = rate.fomc_dates[0];
      const d = new Date(next.date + 'T12:00:00Z');
      fomcHTML = `${d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })} ${next.label}`;
    }

    el.innerHTML = `
      <span class="rate-item">
        <span class="label">目标利率</span>
        <span class="value gold">${targetStr}</span>
      </span>
      <span class="rate-divider">·</span>
      <span class="rate-item">
        <span class="label">有效利率</span>
        <span class="value blue">${effStr}</span>
      </span>
      <span class="rate-divider">·</span>
      <span class="rate-item">
        <span class="label">下次FOMC</span>
        <span class="value">${fomcHTML}</span>
      </span>
    `;
  };

  // ---- Start ----
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      app.init();
      if (typeof SITE_DATA !== 'undefined' && SITE_DATA?.fed_rate) app.updateRateBar(SITE_DATA);
    });
  } else {
    app.init();
    if (typeof SITE_DATA !== 'undefined' && SITE_DATA?.fed_rate) app.updateRateBar(SITE_DATA);
  }

  // Expose for debugging
  window.FED_NO_WATCH = app;
})();
