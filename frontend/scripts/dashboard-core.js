// frontend/scripts/dashboard-core.js
// Dashboard core logic — feature UIs + backend integration
// Replace your existing dashboard-core.js contents with this file.

(function () {
  const API_ROOT = window.__API_BASE ? window.__API_BASE : ''; // empty = same origin
  const API = {
    detectDisease: API_ROOT + '/detect_disease',
    predictCrop: API_ROOT + '/predict_crop',
    fertilizer: API_ROOT + '/fertilizer',
    irrigation: API_ROOT + '/irrigation_advice',
    marketPrice: API_ROOT + '/market_price',
    predictYield: API_ROOT + '/predict_yield'
  };

  // -------------------------
  // Utilities
  // -------------------------
  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function showToast(msg, isError = false) {
    let t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      t.style.position = 'fixed';
      t.style.right = '20px';
      t.style.bottom = '20px';
      t.style.padding = '10px 14px';
      t.style.borderRadius = '8px';
      t.style.color = '#fff';
      t.style.zIndex = 9999;
      document.body.appendChild(t);
    }
    t.style.background = isError ? '#d32f2f' : '#2e7d32';
    t.textContent = msg;
    t.style.display = 'block';
    setTimeout(() => (t.style.display = 'none'), 3500);
  }

  async function fetchJson(url, opts = {}) {
    const r = await fetch(url, opts);
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`HTTP ${r.status} ${text}`);
    }
    return r.json();
  }

  // simple svg sparkline
  function renderSparkline(values = []) {
    if (!values || !values.length) return '';
    const w = 300, h = 40, pad = 2;
    const min = Math.min(...values), max = Math.max(...values);
    const span = max - min || 1;
    const step = w / Math.max(values.length - 1, 1);
    const path = values.map((v, i) => {
      const x = i * step;
      const y = h - ((v - min) / span) * (h - pad * 2) - pad;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');
    return `<svg width="${w}" height="${h}" style="display:block;margin-top:8px"><path d="${path}" stroke="#4caf50" fill="none" stroke-width="2"/></svg>`;
  }

  // Ensure i18n applied after dynamic DOM modifications
  function applyI18nSafe() {
    if (window.i18n && typeof window.i18n.applyTranslations === 'function') {
      try { window.i18n.applyTranslations(); } catch (e) { console.warn('i18n apply error', e); }
    }
  }

  // -------------------------
  // Feature UIs
  // Each function accepts container element and fills it
  // -------------------------
  async function showDiseaseFeature(container) {
    container.innerHTML = `
      <div class="card">
        <h3 data-i18n="feature.disease.title">Disease Detection</h3>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          <div style="flex:1;min-width:260px">
            <input id="dFile" type="file" accept="image/*"><br>
            <div class="preview" id="dPreview" style="margin-top:10px">No image selected</div>
            <div style="margin-top:8px" class="actions">
              <button class="btn btn-use" id="dDetectBtn">Detect</button>
              <button class="btn" id="dClearBtn">Clear</button>
            </div>
          </div>
          <div style="flex:1;min-width:260px">
            <div style="font-weight:700">Result</div>
            <pre id="dResult" class="result-pre">No detection yet.</pre>
            <div id="dSavedImageLink" style="margin-top:8px"></div>
          </div>
        </div>
      </div>
    `;
    applyI18nSafe();

    const dFileInput = document.getElementById('dFile');
    const dPreview = document.getElementById('dPreview');

    dFileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) { dPreview.innerHTML = 'No image selected'; return; }
      const url = URL.createObjectURL(f);
      dPreview.innerHTML = `<img src="${escapeHtml(url)}" style="width:100%;height:100%;object-fit:cover"/>`;
    });

    document.getElementById('dDetectBtn').addEventListener('click', async () => {
      try {
        const files = document.getElementById('dFile').files;
        if (!files || !files[0]) { alert('Select an image'); return; }
        const fd = new FormData(); fd.append('file', files[0]);
        document.getElementById('dResult').textContent = 'Uploading & analyzing...';
        document.getElementById('dSavedImageLink').innerHTML = '';
        const r = await fetch(API.detectDisease, { method: 'POST', body: fd });
        if (!r.ok) { const t = await r.text(); document.getElementById('dResult').textContent = 'Server error: ' + t; showToast('Detection failed', true); return; }
        const data = await r.json();
        const disease = data.disease || 'unknown';
        const confidenceRaw = data.confidence ?? 0;
        const confidence = Math.round((Number(confidenceRaw) || 0) * 100);
        const treatment = data.treatment || 'N/A';
        let out = `Disease: ${disease}\nConfidence: ${confidence}%\n\nTreatment / Notes:\n${treatment}\n`;
        if (data.error) out += `\n(Error: ${data.error})`;
        document.getElementById('dResult').textContent = out;

        if (data.saved_image) {
          const hostOrigin = (new URL(window.location.href)).origin;
          const saved = String(data.saved_image);
          let href = saved;
          if (!/^https?:\/\//.test(saved)) {
            // if backend returned a filesystem path, try to convert to a reachable path by removing server absolute prefix
            if (saved.indexOf('/mnt/') === 0 || saved.indexOf('\\') === 0) {
              // not reachable — show raw
              document.getElementById('dSavedImageLink').innerHTML = `<div class="small-muted">Saved image: ${escapeHtml(saved)}</div>`;
            } else {
              href = saved.startsWith('/') ? hostOrigin + saved : hostOrigin + '/' + saved;
              document.getElementById('dSavedImageLink').innerHTML = `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">View saved image</a>`;
            }
          } else {
            document.getElementById('dSavedImageLink').innerHTML = `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">View saved image</a>`;
          }
        }
        showToast('Detection complete');
      } catch (err) {
        document.getElementById('dResult').textContent = 'Request failed: ' + err.message;
        showToast('Request failed', true);
      }
    });

    document.getElementById('dClearBtn').addEventListener('click', () => {
      document.getElementById('dFile').value = '';
      dPreview.innerHTML = 'No image selected';
      document.getElementById('dResult').textContent = 'Cleared.';
      document.getElementById('dSavedImageLink').innerHTML = '';
    });
  }

  async function showCropFeature(container) {
    container.innerHTML = `
      <div class="card">
        <h3 data-i18n="feature.crop.title">Crop Recommendation</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px">
          <div><label>N</label><input id="mN" type="number" /></div>
          <div><label>P</label><input id="mP" type="number" /></div>
          <div><label>K</label><input id="mK" type="number" /></div>
          <div><label>Temp (°C)</label><input id="mTemperature" type="number" /></div>
          <div><label>Humidity (%)</label><input id="mHumidity" type="number" /></div>
          <div><label>pH</label><input id="mPh" type="number" /></div>
          <div style="grid-column:1/-1"><label>Rainfall (mm)</label><input id="mRainfall" type="number" /></div>
        </div>
        <div style="margin-top:12px" class="actions">
          <button id="mPredictBtn" class="btn btn-use">Predict</button>
          <button id="mClearBtn" class="btn">Clear</button>
        </div>
        <div style="margin-top:12px"><pre id="mResult" class="result-pre">No prediction yet.</pre></div>
      </div>
    `;
    applyI18nSafe();

    document.getElementById('mPredictBtn').addEventListener('click', async () => {
      const payload = {
        N: parseFloat(document.getElementById('mN').value) || 0,
        P: parseFloat(document.getElementById('mP').value) || 0,
        K: parseFloat(document.getElementById('mK').value) || 0,
        temperature: parseFloat(document.getElementById('mTemperature').value) || 0,
        humidity: parseFloat(document.getElementById('mHumidity').value) || 0,
        ph: parseFloat(document.getElementById('mPh').value) || 0,
        rainfall: parseFloat(document.getElementById('mRainfall').value) || 0,
        soil_type: ''
      };
      const resEl = document.getElementById('mResult'); resEl.textContent = 'Calling API...';
      try {
        const r = await fetchJson('/predict_crop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const recommended = Array.isArray(r.recommended) ? r.recommended : (r.recommended ? [r.recommended] : []);
        const reasons = r.reasons || '';
        let out = 'Recommended: ' + (recommended.length ? recommended.join(', ') : 'N/A') + '\n\nWhy:\n' + (reasons || 'N/A');
        if (r.probabilities) out += '\n\nProbabilities:\n' + JSON.stringify(r.probabilities, null, 2);
        resEl.textContent = out;
        showToast('Prediction complete');
      } catch (err) {
        resEl.textContent = 'Request failed: ' + err.message;
        showToast('Request failed', true);
      }
    });

    document.getElementById('mClearBtn').addEventListener('click', () => {
      ['mN', 'mP', 'mK', 'mTemperature', 'mHumidity', 'mPh', 'mRainfall'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
      document.getElementById('mResult').textContent = 'Cleared.';
    });
  }

  async function showFertilizerFeature(container) {
    container.innerHTML = `
      <div class="card">
        <h3 data-i18n="feature.fert.title">Fertilizer Advisor</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div><label>Crop</label><input id="fCrop" placeholder="rice" /></div>
          <div><label>N (current)</label><input id="fN" type="number" /></div>
          <div><label>P (current)</label><input id="fP" type="number" /></div>
          <div><label>K (current)</label><input id="fK" type="number" /></div>
        </div>
        <div class="actions" style="margin-top:12px">
          <button id="fGetBtn" class="btn btn-use">Get Plan</button>
          <button id="fClearBtn" class="btn">Clear</button>
        </div>
        <div style="margin-top:12px">
          <div id="fPlanText" style="font-weight:700">No fertilizer request yet.</div>
          <table id="fTable" class="fert-table" style="display:none">
            <thead><tr><th>Fertilizer</th><th>Quantity (kg/acre)</th><th>Cost (₹)</th></tr></thead>
            <tbody id="fTableBody"></tbody>
            <tfoot><tr style="font-weight:800"><td>Total</td><td id="fTotalKg">-</td><td id="fTotalCost">-</td></tr></tfoot>
          </table>
        </div>
      </div>
    `;
    applyI18nSafe();

    document.getElementById('fGetBtn').addEventListener('click', async () => {
      const payload = { crop: (document.getElementById('fCrop').value || '').trim(), n: parseFloat(document.getElementById('fN').value) || 0, p: parseFloat(document.getElementById('fP').value) || 0, k: parseFloat(document.getElementById('fK').value) || 0 };
      document.getElementById('fPlanText').textContent = 'Calling fertilizer API...';
      document.getElementById('fTable').style.display = 'none';
      try {
        const r = await fetchJson('/fertilizer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const planText = r.fertilizer_plan || r.plan || r.recommendation || '';
        document.getElementById('fPlanText').textContent = planText || 'No plan returned.';
        const breakdown = r.cost_breakdown || r.breakdown || r.details || r.costs || null;
        const tbody = document.getElementById('fTableBody'); tbody.innerHTML = '';
        let totalKg = 0, totalCost = 0;
        if (breakdown && typeof breakdown === 'object' && Object.keys(breakdown).length) {
          document.getElementById('fTable').style.display = '';
          for (const [prod, info] of Object.entries(breakdown)) {
            let kgText = '-', costText = '-';
            if (info === null || info === undefined) { kgText = '-'; costText = '-'; }
            else if (typeof info === 'number') { kgText = Number(info).toFixed(2); }
            else if (typeof info === 'string') { kgText = escapeHtml(info); }
            else if (typeof info === 'object') {
              const kgVal = info.kg ?? info.quantity ?? info.qty ?? info.amount;
              const costVal = info.cost ?? info.price ?? info.cost_inr ?? info.estimated;
              kgText = kgVal !== undefined ? Number(kgVal).toFixed(2) : '-';
              costText = costVal !== undefined ? Number(costVal).toFixed(2) : '-';
            }
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${escapeHtml(prod)}</td><td>${kgText}</td><td>${costText}</td>`;
            tbody.appendChild(tr);
            const kgNum = Number(String(kgText).replace(/[^0-9.\-]/g, '')) || 0;
            const costNum = Number(String(costText).replace(/[^0-9.\-]/g, '')) || 0;
            totalKg += kgNum;
            totalCost += costNum;
          }
          document.getElementById('fTotalKg').textContent = Number(totalKg).toFixed(2);
          document.getElementById('fTotalCost').textContent = Number(totalCost).toFixed(2);
        } else {
          document.getElementById('fTable').style.display = 'none';
        }
        window.__lastFertilizerPlan = r;
        showToast('Fertilizer plan ready');
      } catch (err) {
        document.getElementById('fPlanText').textContent = 'Request failed: ' + err.message;
        showToast('Request failed', true);
      }
    });

    document.getElementById('fClearBtn').addEventListener('click', () => {
      ['fCrop', 'fN', 'fP', 'fK'].forEach(i => { const el = document.getElementById(i); if (el) el.value = ''; });
      document.getElementById('fPlanText').textContent = 'Cleared'; document.getElementById('fTable').style.display = 'none'; window.__lastFertilizerPlan = null;
    });
  }

  async function showIrrigationFeature(container) {
    container.innerHTML = `
      <div class="card">
        <h3 data-i18n="feature.irrigation.title">Irrigation Advice</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div><label>Location</label><input id="irLocation" /></div>
          <div><label>Crop</label><input id="irCrop" /></div>
          <div><label>Soil moisture (%)</label><input id="irSoil" type="number" /></div>
          <div><label>Area (acres)</label><input id="irArea" type="number" value="1" /></div>
        </div>
        <div class="actions" style="margin-top:12px">
          <button id="irGetBtn" class="btn btn-use">Get Advice</button>
          <button id="irClearBtn" class="btn">Clear</button>
        </div>
        <div style="margin-top:12px"><div id="irPlaceholder" class="small-muted">Enter details to receive advice</div><div id="irDataArea" style="display:none;margin-top:10px" class="card"></div></div>
      </div>
    `;
    applyI18nSafe();

    document.getElementById('irGetBtn').addEventListener('click', async () => {
      const areaInput = document.getElementById('irArea').value;
      const payload = {
        location: document.getElementById('irLocation').value || '',
        crop: document.getElementById('irCrop').value || '',
        soil_moisture: document.getElementById('irSoil').value ? parseFloat(document.getElementById('irSoil').value) : null,
        area_acres: areaInput ? parseFloat(areaInput) : 1.0
      };
      if (!payload.location && payload.soil_moisture === null && !payload.crop) { showToast('Provide location or soil moisture or crop', true); return; }
      try {
        document.getElementById('irPlaceholder').textContent = 'Analyzing...';
        const r = await fetchJson('/irrigation_advice', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const areaEl = document.getElementById('irDataArea');
        areaEl.style.display = 'block';
        areaEl.innerHTML = `
          <div style="font-weight:700">${escapeHtml(r.when || 'N/A')}</div>
          <div style="color:#666;margin-top:6px">${escapeHtml(r.notes || '')}</div>
          <div style="margin-top:10px"><strong>Water required:</strong> ${r.how_much_mm !== undefined ? escapeHtml(String(r.how_much_mm)) + ' mm' : 'N/A'}</div>
          <div style="margin-top:6px"><strong>Volume:</strong> ${r.how_much_liters !== undefined ? Number(r.how_much_liters).toLocaleString() + ' L' : 'N/A' } for ${payload.area_acres || 1} acre(s)</div>
          ${r.pump_duration_minutes ? `<div style="margin-top:6px"><strong>Pump runtime:</strong> ${escapeHtml(String(r.pump_duration_minutes))} minutes</div>` : ''}
        `;
        document.getElementById('irPlaceholder').textContent = '';
        showToast('Irrigation advice ready');
      } catch (err) {
        document.getElementById('irPlaceholder').textContent = 'Error: ' + err.message;
        showToast('Request failed', true);
      }
    });

    document.getElementById('irClearBtn').addEventListener('click', () => {
      ['irLocation', 'irCrop', 'irSoil', 'irArea'].forEach(i => { const el = document.getElementById(i); if (el) el.value = ''; });
      document.getElementById('irDataArea').style.display = 'none';
    });
  }

  // -------------------------
  // Market & Yield (adapted to your existing backend routes)
  // Market uses POST /market_price
  // Yield uses POST /predict_yield
  // -------------------------
  async function showMarketFeature(container) {
    container.innerHTML = `
      <div class="card">
        <h3 data-i18n="feature.market.title">Market Insights</h3>
        <div style="display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end">
          <div>
            <label>Crop</label><input id="marketCrop" value="tomato"/>
            <label>Location</label><input id="marketLoc" value="local"/>
          </div>
          <div style="text-align:right">
            <button id="marketGetBtn" class="btn btn-use">Get Insights</button>
          </div>
        </div>
        <div id="marketResult" style="margin-top:12px"></div>
      </div>
    `;
    applyI18nSafe();

    document.getElementById('marketGetBtn').addEventListener('click', async () => {
      const crop = document.getElementById('marketCrop').value || 'tomato';
      const location = document.getElementById('marketLoc').value || 'local';
      const rEl = document.getElementById('marketResult');
      rEl.innerHTML = 'Loading...';
      try {
        const res = await fetchJson('/market_price', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ crop, location }) });
        let html = `<div><strong>Trend:</strong> ${escapeHtml(res.predicted_trend || 'N/A')}</div>`;
        if (res.best_market) html += `<div><strong>Best market:</strong> ${escapeHtml(res.best_market)}</div>`;
        html += `<div style="margin-top:8px"><strong>Current prices</strong></div>`;
        html += `<table style="width:100%;margin-top:6px;border-collapse:collapse"><thead><tr><th>Market</th><th>Price</th></tr></thead><tbody>`;
        const prices = res.current_prices || {};
        for (const [m, p] of Object.entries(prices)) {
          html += `<tr><td>${escapeHtml(m)}</td><td>${escapeHtml(String(p))}</td></tr>`;
        }
        html += `</tbody></table>`;
        html += `<div style="margin-top:8px;color:#666">Recommendation: ${escapeHtml(res.predicted_trend || 'N/A')}</div>`;
        rEl.innerHTML = html;
        applyI18nSafe();
      } catch (err) {
        rEl.innerHTML = `<div style="color:var(--danger)">Error: ${escapeHtml(err.message)}</div>`;
      }
    });
  }

  async function showYieldFeature(container) {
    container.innerHTML = `
      <div class="card">
        <h3 data-i18n="feature.yield.title">Yield Prediction</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div><label>Crop</label><input id="yCrop" value="rice" /></div>
          <div><label>Area (acres)</label><input id="yArea" type="number" value="1" /></div>
        </div>
        <div style="margin-top:12px" class="actions">
          <button id="yPredictBtn" class="btn btn-use">Predict Yield</button>
          <button id="yClearBtn" class="btn">Clear</button>
        </div>
        <div id="yResult" style="margin-top:12px"></div>
      </div>
    `;
    applyI18nSafe();

    document.getElementById('yPredictBtn').addEventListener('click', async () => {
      const payload = {
        crop: document.getElementById('yCrop').value || 'rice',
        area_acres: parseFloat(document.getElementById('yArea').value) || 1
      };
      const rEl = document.getElementById('yResult');
      rEl.innerHTML = 'Predicting...';
      try {
        const res = await fetchJson('/predict_yield', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        // your backend returns predicted_yield_per_acre, total_harvest, estimated_income
        let html = `<div><strong>Predicted yield per acre:</strong> ${escapeHtml(String(res.predicted_yield_per_acre || '-'))}</div>`;
        html += `<div><strong>Total harvest:</strong> ${escapeHtml(String(res.total_harvest || '-'))}</div>`;
        if (res.estimated_income !== undefined) html += `<div><strong>Estimated income:</strong> ₹${escapeHtml(String(res.estimated_income || '-'))}</div>`;
        html += `<div style="margin-top:8px;color:#666">Note: units depend on backend settings.</div>`;
        rEl.innerHTML = html;
        applyI18nSafe();
      } catch (err) {
        rEl.innerHTML = `<div style="color:var(--danger)">Error: ${escapeHtml(err.message)}</div>`;
      }
    });

    document.getElementById('yClearBtn').addEventListener('click', () => {
      document.getElementById('yCrop').value = '';
      document.getElementById('yArea').value = '';
      document.getElementById('yResult').innerHTML = 'Cleared';
    });
  }

  // -------------------------
  // selectFeature implementation used by your dashboard
  // fills #featureArea with selected feature UI
  // -------------------------
  window.selectFeature = function (name) {
    const area = document.getElementById('featureArea');
    if (!area) return;
    area.innerHTML = '';
    // ensure translations are not stale
    const nm = String(name || '').toLowerCase();
    if (nm === 'disease') {
      showDiseaseFeature(area);
    } else if (nm === 'crop') {
      showCropFeature(area);
    } else if (nm === 'fert') {
      showFertilizerFeature(area);
    } else if (nm === 'irrigation') {
      showIrrigationFeature(area);
    } else if (nm === 'market') {
      showMarketFeature(area);
    } else if (nm === 'yield') {
      showYieldFeature(area);
    } else {
      area.innerHTML = `<div class="card"><em data-i18n="dashboard.select_feature">Select a feature to start</em></div>`;
      applyI18nSafe();
    }
  };

  // default panel
  document.addEventListener('DOMContentLoaded', function () {
    const area = document.getElementById('featureArea');
    if (area) {
      area.innerHTML = '<div class="card"><em data-i18n="dashboard.select_feature">Select a feature to start</em></div>';
      applyI18nSafe();
    }

    // reapply i18n a short time after core loads, in case other scripts changed DOM
    setTimeout(() => applyI18nSafe(), 120);
  });

})();
