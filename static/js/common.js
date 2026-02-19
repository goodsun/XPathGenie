// XPathGenie — shared utilities
// Key obfuscation (not encryption — just hides from casual DevTools inspection)
function obfuscateKey(key) { return btoa(key.split('').reverse().join('')); }
function deobfuscateKey(stored) { try { return atob(stored).split('').reverse().join(''); } catch { return ''; } }

// Security modal styles (injected once)
(function() {
  if (document.getElementById('xpg-modal-styles')) return;
  const s = document.createElement('style');
  s.id = 'xpg-modal-styles';
  s.textContent = `.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:10000;align-items:center;justify-content:center}.modal-overlay.active{display:flex}.modal-box{background:#1a1a2e;border:1px solid #3a2a5a;border-radius:12px;padding:24px;max-width:420px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.5)}.modal-box h3{color:#ffd700;font-size:1rem;margin-bottom:12px}.modal-box ul{list-style:none;padding:0;margin:0 0 16px 0}.modal-box li{color:#ccc;font-size:.85rem;padding:6px 0;border-bottom:1px solid #2a1a3a}.modal-box li::before{content:'⚠️ '}.modal-box li:last-child{border-bottom:none}.modal-box li:last-child::before{content:'💡 '}.modal-box a{color:#b366ff}.modal-actions{display:flex;gap:10px;justify-content:flex-end}.modal-actions button{padding:8px 20px;border:none;border-radius:8px;font-size:.85rem;cursor:pointer;font-family:inherit}.modal-cancel{background:#333;color:#aaa}.modal-cancel:hover{background:#444}.modal-confirm{background:linear-gradient(135deg,#b366ff,#8a2be2);color:#fff}.modal-confirm:hover{opacity:.9}`;
  document.head.appendChild(s);
})();

// Security modal for API key storage confirmation
function showSecurityModal(isJp) {
  // Auto-create modal if not in DOM
  if (!document.getElementById('securityModal')) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'securityModal';
    overlay.innerHTML = '<div class="modal-box" id="securityModalBox"></div>';
    document.body.appendChild(overlay);
  }
  const modal = document.getElementById('securityModal');
  const box = document.getElementById('securityModalBox');
  if (isJp === undefined) isJp = (document.documentElement.lang === 'ja');
  box.innerHTML = isJp
    ? `<h3>🔐 セキュリティに関する注意</h3>
      <ul>
        <li>APIキーはブラウザのlocalStorageに保存されます</li>
        <li>ブラウザ拡張機能やXSS攻撃でアクセスされる可能性があります</li>
        <li>機密性の高い用途ではRememberをOFFにしてください</li>
        <li>キーは <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a> でいつでも再生成できます</li>
      </ul>
      <div class="modal-actions">
        <button class="modal-cancel" id="modalCancel">キャンセル</button>
        <button class="modal-confirm" id="modalConfirm">保存する</button>
      </div>`
    : `<h3>🔐 Security Notice</h3>
      <ul>
        <li>Your API key will be stored in localStorage</li>
        <li>It could be accessed by browser extensions or XSS attacks</li>
        <li>For sensitive use cases, keep Remember OFF</li>
        <li>You can regenerate your key anytime at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a></li>
      </ul>
      <div class="modal-actions">
        <button class="modal-cancel" id="modalCancel">Cancel</button>
        <button class="modal-confirm" id="modalConfirm">Save</button>
      </div>`;
  return new Promise(resolve => {
    modal.classList.add('active');
    const onConfirm = () => { cleanup(); resolve(true); };
    const onCancel = () => { cleanup(); resolve(false); };
    const onOverlay = (e) => { if (e.target === modal) { cleanup(); resolve(false); } };
    const cleanup = () => {
      modal.classList.remove('active');
      document.getElementById('modalConfirm').removeEventListener('click', onConfirm);
      document.getElementById('modalCancel').removeEventListener('click', onCancel);
      modal.removeEventListener('click', onOverlay);
    };
    document.getElementById('modalConfirm').addEventListener('click', onConfirm);
    document.getElementById('modalCancel').addEventListener('click', onCancel);
    modal.addEventListener('click', onOverlay);
  });
}
