const { createApp, ref, computed, watch } = Vue;

createApp({
  setup() {
    const apiKey = ref(localStorage.getItem('xpathgenie_api_key') || '');
    const showKey = ref(false);
    const urlText = ref(localStorage.getItem('xpathgenie_urls') || '');
    const wantlistText = ref(localStorage.getItem('xpathgenie_wantlist') || '');
    const mode = ref(localStorage.getItem('xpathgenie_mode') || 'discover');  // 'discover' or 'wantlist'
    const loading = ref(false);
    const error = ref(null);
    const savedResult = localStorage.getItem('xpathgenie_result');
    const result = ref(savedResult ? JSON.parse(savedResult) : null);
    const elapsed = ref(0);
    const copied = ref(false);
    const editing = ref(null);
    const editName = ref('');
    let timer = null;

    const elapsedStr = computed(() => elapsed.value + 's');
    const savedAtStr = computed(() => {
      if (!result.value?._savedAt) return '';
      return new Date(result.value._savedAt).toLocaleString();
    });

    const wantlistPlaceholder = `{
  "original_id": "求人ID・管理番号",
  "title": "求人タイトル",
  "facility_name": "勤務先の施設名・会社名",
  "prefecture": "都道府県・市区町村",
  "station": "最寄り駅",
  "access": "アクセス方法・徒歩何分",
  "price": "給与・時給・月給・年収",
  "occupation": "職種（看護師、介護職、薬剤師等）",
  "contract": "雇用形態（正社員、契約社員、パート等）",
  "detail": "仕事内容・業務内容",
  "working_hours": "勤務時間・シフト",
  "holiday": "休日・休暇",
  "welfare_program": "福利厚生・社会保険"
}`;

    function confidenceColor(c) {
      if (c >= 0.8) return '#4caf50';
      if (c >= 0.5) return '#ff9800';
      return '#f44336';
    }

    async function analyzeUrls() {
      const urls = urlText.value.split('\n').map(u => u.trim().replace(/^\d+[\.\)\]\s:]+\s*/, '')).filter(u => u.startsWith('http'));
      if (!urls.length) return;
      if (!apiKey.value.trim()) {
        error.value = 'Please enter your Gemini API key first.';
        return;
      }

      loading.value = true;
      error.value = null;
      result.value = null;
      elapsed.value = 0;
      timer = setInterval(() => elapsed.value++, 1000);

      const body = { urls, api_key: apiKey.value.trim() };

      // Parse wantlist if in wantlist mode
      if (mode.value === 'wantlist' && wantlistText.value.trim()) {
        try {
          body.wantlist = JSON.parse(wantlistText.value.trim());
        } catch (e) {
          error.value = 'Invalid JSON in Want List: ' + e.message;
          loading.value = false;
          clearInterval(timer);
          return;
        }
      }

      try {
        const resp = await fetch('api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!resp.ok) {
          error.value = data.error || 'Unknown error';
        } else {
          result.value = data;
          // Persist full result for page reload + save flat mappings for Aladdin
          data._savedAt = new Date().toISOString();
          localStorage.setItem('xpathgenie_result', JSON.stringify(data));
          const m = {};
          for (const [k, v] of Object.entries(data.mappings)) { m[k] = v.xpath; }
          localStorage.setItem('xpathgenie_mappings', JSON.stringify(m, null, 2));
        }
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
        clearInterval(timer);
      }
    }

    function startEdit(field) {
      editing.value = field;
      editName.value = field;
    }

    function renameField(oldName) {
      const newName = editName.value.trim();
      editing.value = null;
      if (!newName || newName === oldName || !result.value) return;
      const m = result.value.mappings;
      if (m[newName]) return;
      const val = m[oldName];
      delete m[oldName];
      m[newName] = val;
    }

    function getMappingsOnly() {
      if (!result.value) return {};
      const out = {};
      for (const [k, v] of Object.entries(result.value.mappings)) {
        out[k] = v.xpath;
      }
      return out;
    }

    function copyJSON() {
      navigator.clipboard.writeText(JSON.stringify(getMappingsOnly(), null, 2));
      flashCopied();
    }

    function copyYAML() {
      const m = getMappingsOnly();
      const lines = ['mapping:'];
      for (const [k, v] of Object.entries(m)) {
        lines.push(`  ${k}: "${v}"`);
      }
      navigator.clipboard.writeText(lines.join('\n'));
      flashCopied();
    }

    function openInAladdin() {
      const m = getMappingsOnly();
      localStorage.setItem('xpathgenie_mappings', JSON.stringify(m, null, 2));
      // URLs are already shared via xpathgenie_urls
      window.location.href = 'aladdin.html';
    }

    function flashCopied() {
      copied.value = true;
      setTimeout(() => copied.value = false, 2000);
    }

    function saveApiKey() {
      localStorage.setItem('xpathgenie_api_key', apiKey.value);
    }

    watch(apiKey, (v) => localStorage.setItem('xpathgenie_api_key', v));
    watch(urlText, (v) => localStorage.setItem('xpathgenie_urls', v));
    watch(wantlistText, (v) => localStorage.setItem('xpathgenie_wantlist', v));
    watch(mode, (v) => localStorage.setItem('xpathgenie_mode', v));

    return {
      apiKey, showKey, saveApiKey,
      urlText, wantlistText, mode, wantlistPlaceholder,
      loading, error, result, elapsed, elapsedStr, savedAtStr, copied,
      editing, editName,
      analyzeUrls, startEdit, renameField, confidenceColor,
      copyJSON, copyYAML, openInAladdin,
    };
  }
}).mount('#app');
