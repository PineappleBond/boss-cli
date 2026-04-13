// Boss直聘 Cookie 提取器 - 后台服务
// 负责定时提取 Cookie 并发送到本地服务

const ALARM_NAME = 'refresh-zhipin-cookies';
const SERVER_URL = 'http://127.0.0.1:9876/import-cookies';

// 获取所有 zhipin.com 相关的 cookie
async function getZhipinCookies() {
  let allCookies = [];
  
  try {
    allCookies = await chrome.cookies.getAll({});
  } catch (e) {
    console.log('获取所有 cookie 失败:', e);
    return [];
  }
  
  // 过滤出 zhipin.com 相关的 cookie
  const zhipinCookies = allCookies.filter(cookie => {
    const domain = cookie.domain || '';
    return domain.includes('zhipin.com') || 
           domain.endsWith('zhipin.com') ||
           domain.includes('.zhipin.');
  });
  
  // 去重
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

// 发送 Cookie 到本地服务
async function sendCookiesToServer(cookies) {
  if (cookies.length === 0) {
    console.log('没有 Cookie，跳过发送');
    return { success: false, error: '没有 Cookie' };
  }
  
  const cookieDict = {};
  for (const cookie of cookies) {
    cookieDict[cookie.name] = cookie.value;
  }
  
  try {
    const response = await fetch(SERVER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies: cookieDict })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ Cookie 发送成功:', result);
      
      // 保存最后更新时间到 storage
      await chrome.storage.local.set({
        lastUpdate: new Date().toISOString(),
        cookieCount: cookies.length,
        hasStoken: '__zp_stoken__' in cookieDict
      });
      
      return { success: true, data: result };
    } else {
      console.log('❌ Cookie 发送失败:', response.status);
      return { success: false, error: `HTTP ${response.status}` };
    }
  } catch (e) {
    console.log('❌ 发送请求失败:', e.message);
    return { success: false, error: e.message };
  }
}

// 定时任务：提取并发送 Cookie
async function refreshCookies() {
  console.log('⏰ 定时任务触发：刷新 Cookie');
  
  const cookies = await getZhipinCookies();
  
  // 检查是否有必要的 cookie
  const required = ['wt2', 'wbg', 'zp_at'];
  const cookieNames = cookies.map(c => c.name);
  const hasRequired = required.every(n => cookieNames.includes(n));
  
  if (!hasRequired) {
    console.log('⚠️ 缺少必要 Cookie，可能未登录');
    await chrome.storage.local.set({
      lastUpdate: new Date().toISOString(),
      status: 'not_logged_in'
    });
    return;
  }
  
  await sendCookiesToServer(cookies);
}

// 监听定时器
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    refreshCookies();
  }
});

// 扩展安装/更新时启动定时任务
chrome.runtime.onInstalled.addListener(() => {
  console.log('扩展已安装/更新，启动定时任务');
  
  // 创建定时器：每 5 分钟执行一次
  chrome.alarms.create(ALARM_NAME, {
    delayInMinutes: 0.1,  // 6秒后首次执行
    periodInMinutes: 5     // 每5分钟执行
  });
  
  // 立即执行一次
  refreshCookies();
});

// 扩展启动时也启动定时任务
chrome.runtime.onStartup.addListener(() => {
  console.log('浏览器启动，恢复定时任务');
  
  chrome.alarms.get(ALARM_NAME, (alarm) => {
    if (!alarm) {
      chrome.alarms.create(ALARM_NAME, {
        delayInMinutes: 0.1,
        periodInMinutes: 5
      });
    }
  });
  
  // 立即执行一次
  refreshCookies();
});

// 监听来自 popup 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'get-status') {
    chrome.storage.local.get(['lastUpdate', 'cookieCount', 'hasStoken', 'status'], (data) => {
      sendResponse(data);
    });
    return true;  // 保持消息通道开放
  }
  
  if (message.action === 'refresh-now') {
    refreshCookies().then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
  
  if (message.action === 'set-interval') {
    const minutes = message.minutes || 5;
    chrome.alarms.clear(ALARM_NAME, () => {
      chrome.alarms.create(ALARM_NAME, {
        delayInMinutes: 0.1,
        periodInMinutes: minutes
      });
    });
    sendResponse({ success: true, interval: minutes });
    return true;
  }
});