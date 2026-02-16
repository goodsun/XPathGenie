const { createApp, ref, computed } = Vue;

createApp({
  setup() {
    const urlText = ref('');
    const loading = ref(false);
    const error = ref(null);
    const result = ref(null);
    const elapsed = ref(0);
    const copied = ref(false);
    const editing = ref(null);
    const editName = ref('');
    let timer = null;

    const elapsedStr = computed(() => elapsed.value + 's');

    function confidenceColor(c) {
      if (c >= 0.8) return '#4caf50';
      if (c >= 0.5) return '#ff9800';
      return '#f44336';
    }

    async function analyzeUrls() {
      const urls = urlText.value.split('\n').map(u => u.trim()).filter(Boolean);
      if (!urls.length) return;

      loading.value = true;
      error.value = null;
      result.value = null;
      elapsed.value = 0;
      timer = setInterval(() => elapsed.value++, 1000);

      try {
        const resp = await fetch('api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ urls }),
        });
        const data = await resp.json();
        if (!resp.ok) {
          error.value = data.error || 'Unknown error';
        } else {
          result.value = data;
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
      if (m[newName]) return; // name collision
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

    function flashCopied() {
      copied.value = true;
      setTimeout(() => copied.value = false, 2000);
    }

    return {
      urlText, loading, error, result, elapsed, elapsedStr, copied,
      editing, editName,
      analyzeUrls, startEdit, renameField, confidenceColor,
      copyJSON, copyYAML,
    };
  }
}).mount('#app');
