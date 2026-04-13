// Boss直聘 Cookie 提取器

// 获取所有 zhipin.com 相关的 cookie
async function getZhipinCookies() {
  let allCookies = [];
  
  try {
    allCookies = await chrome.cookies.getAll({});
  } catch (e) {
    console.log('获取所有 cookie 失败:', e);
    return [];
  }
  
  const zhipinCookies = allCookies.filter(cookie => {
    const domain = cookie.domain || '';
    return domain.includes('zhipin.com') || 
           domain.endsWith('zhipin.com') ||
           domain.includes('.zhipin.');
  });
  
  const uniqueCookies = [];
  const seen = new Set();
  for (const cookie of zhipinCookies) {
    const key = `${cookie.name}:${cookie.value}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueCookies.push(cookie);
    }
  }
  
  return uniqueCookies;
}

function formatCookiesForBossCli(cookies) {
  const cookieDict = {};
  for (const cookie of cookies) {
    cookieDict[cookie.name] = cookie.value;
  }
  return cookieDict;
}

function formatCookiesAsString(cookies) {
  return cookies.map(c => `${c.name}=${c.value}`).join('; ');
}

function checkRequiredCookies(cookies) {
  const required = ['wt2', 'wbg', 'zp_at'];
  const cookieNames = cookies.map(c => c.name);
  const missingRequired = required.filter(n => !cookieNames.includes(n));
  const hasStoken = cookieNames.includes('__zp_stoken__');
  
  return {
    valid: missingRequired.length === 0,
    missingRequired,
    hasStoken,
    cookieNames
  };
}

function renderCookieList(cookies) {
  const listEl = document.getElementById('cookie-list');
  listEl.innerHTML = '';
  
  const sortedCookies = [...cookies].sort((a, b) => {
    if (a.name === '__zp_stoken__') return -1;
    if (b.name === '__zp_stoken__') return 1;
    if (a.name.startsWith('zp_') || a.name.startsWith('wt') || a.name.startsWith('wbg')) return -1;
    if (b.name.startsWith('zp_') || b.name.startsWith('wt') || b.name.startsWith('wbg')) return 1;
    return a.name.localeCompare(b.name);
  });
  
  for (const cookie of sortedCookies) {
    const item = document.createElement('div');
    item.className = 'cookie-item';
    
    const nameEl = document.createElement('span');
    nameEl.className = 'cookie-name';
    if (cookie.name === '__zp_stoken__') {
      nameEl.innerHTML = `<span class="highlight">⭐ ${cookie.name}</span>`;
    } else if (cookie.name.startsWith('wt') || cookie.name.startsWith('wbg') || cookie.name.startsWith('zp_')) {
      nameEl.textContent = `🔑 ${cookie.name}`;
    } else {
      nameEl.textContent = cookie.name;
    }
    
    const valueEl = document.createElement('span');
    valueEl.className = 'cookie-value';
    const displayValue = cookie.value.length > 50 
      ? cookie.value.substring(0, 50) + '...' 
      : cookie.value;
    valueEl.textContent = displayValue;
    
    item.appendChild(nameEl);
    item.appendChild(document.createElement('br'));
    item.appendChild(valueEl);
    listEl.appendChild(item);
  }
}

function showStatus(message, type = 'info') {
  const statusEl = document.getElementById('status');
  statusEl.className = `status ${type}`;
  statusEl.textContent = message;
}

function updateAutoRefreshStatus(data) {
  const statusEl = document.getElementById('auto-refresh-status');
  
  if (data.lastUpdate) {
    const lastUpdate = new Date(data.lastUpdate);
    const now = new Date();
    const diffSeconds = Math.floor((now - lastUpdate) / 1000);
    
    let timeAgo;
    if (diffSeconds < 60) {
      timeAgo = `${diffSeconds} 秒前`;
    } else if (diffSeconds < 3600) {
      timeAgo = `${Math.floor(diffSeconds / 60)} 分钟前`;
    } else {
      timeAgo = `${Math.floor(diffSeconds / 3600)} 小时前`;
    }
    
    let statusText = `✅ 上次同步: ${timeAgo} (${data.cookieCount || 0} 个 Cookie)`;
    if (data.hasStoken) {
      statusText += ' [含 ⭐__zp_stoken__]';
    }
    
    if (data.status === 'not_logged_in') {
      statusText = '⚠️ 未检测到登录状态';
    }
    
    statusEl.textContent = statusText;
  } else {
    statusEl.textContent = '⏳ 等待首次同步...';
  }
}

let currentCookies = [];

async function main() {
  try {
    // 获取自动刷新状态
    chrome.runtime.sendMessage({ action: 'get-status' }, (statusData) => {
      if (statusData) {
        updateAutoRefreshStatus(statusData);
      }
    });
    
    // 获取当前 Cookie
    const cookies = await getZhipinCookies();
    currentCookies = cookies;
    
    if (cookies.length === 0) {
      showStatus('❌ 未找到 Boss直聘 Cookie。请先在浏览器中登录 zhipin.com', 'error');
      return;
    }
    
    const check = checkRequiredCookies(cookies);
    
    if (!check.valid) {
      showStatus(`❌ 缺少必要 Cookie: ${check.missingRequired.join(', ')}`, 'error');
      return;
    }
    
    let statusMsg = `✅ 已获取 ${cookies.length} 个 Cookie`;
    if (check.hasStoken) {
      statusMsg += '（含 ⭐__zp_stoken__）';
    }
    showStatus(statusMsg, 'success');
    
    renderCookieList(cookies);
    document.getElementById('cookie-section').style.display = 'block';
    
  } catch (e) {
    showStatus(`❌ 获取 Cookie 失败: ${e.message}`, 'error');
  }
}

// 复制到剪贴板
document.getElementById('copy-btn').addEventListener('click', async () => {
  const cookieStr = formatCookiesAsString(currentCookies);
  try {
    await navigator.clipboard.writeText(cookieStr);
    showStatus('✅ 已复制到剪贴板！', 'success');
  } catch (e) {
    showStatus('❌ 复制失败: ' + e.message, 'error');
  }
});

// 导出 JSON
document.getElementById('export-btn').addEventListener('click', () => {
  const cookieDict = formatCookiesForBossCli(currentCookies);
  const json = JSON.stringify(cookieDict, null, 2);
  
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = 'boss_cookies.json';
  a.click();
  
  URL.revokeObjectURL(url);
  showStatus('✅ 已导出 JSON 文件！', 'success');
});

// 导入到 boss-cli
document.getElementById('login-btn').addEventListener('click', async () => {
  const cookieDict = formatCookiesForBossCli(currentCookies);
  
  try {
    const response = await fetch('http://127.0.0.1:9876/import-cookies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies: cookieDict })
    });
    
    if (response.ok) {
      const result = await response.json();
      showStatus(`✅ ${result.message || '已导入！'}`, 'success');
    } else {
      showStatus('❌ 导入失败，请检查本地服务是否启动', 'error');
    }
  } catch (e) {
    showStatus('❌ 无法连接本地服务: ' + e.message, 'error');
  }
});

// 立即刷新按钮
document.getElementById('refresh-now-btn').addEventListener('click', () => {
  showStatus('🔄 正在刷新...', 'info');
  chrome.runtime.sendMessage({ action: 'refresh-now' }, (result) => {
    if (result && result.success) {
      showStatus('✅ 已手动刷新！', 'success');
      // 重新获取状态
      chrome.runtime.sendMessage({ action: 'get-status' }, (statusData) => {
        if (statusData) {
          updateAutoRefreshStatus(statusData);
        }
      });
    }
  });
});

// 切换刷新间隔
document.getElementById('interval-select').addEventListener('change', (e) => {
  const minutes = parseInt(e.target.value);
  chrome.runtime.sendMessage({ action: 'set-interval', minutes: minutes }, (result) => {
    if (result && result.success) {
      showStatus(`✅ 已设置刷新间隔为 ${minutes} 分钟`, 'success');
    }
  });
});

// 启动
main();