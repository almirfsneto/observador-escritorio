'use strict';
importScripts('bridge_protocol.js');
const ACTIONS = new Set(['save','review','download','rename','move','register','open_menu','select_menu','select_tab','submit','navigate','transition']);
const ROLES = new Set(['button','menuitem','tab','window','control']);
const allowed = value => {
  try { const u = new URL(value); return u.origin === 'http://127.0.0.1:8765' && u.pathname.startsWith('/synthetic-lab/') && !u.username && !u.password; }
  catch { return false; }
};
let chain = Promise.resolve();
async function handle(message, sender) {
  if (!message || typeof message !== 'object' || sender.id !== chrome.runtime.id) return {ok:false};
  const popup = sender.url === chrome.runtime.getURL('popup.html');
  const tabId = popup ? message.tabId : sender.tab?.id;
  if (!Number.isInteger(tabId)) return {ok:false};
  const tab = popup ? await chrome.tabs.get(tabId) : sender.tab;
  if (!allowed(tab?.url) || (!popup && !allowed(sender.url))) return {ok:false};
  const saved = await chrome.storage.session.get('sessions');
  const sessions = saved.sessions || {};
  let s = sessions[tabId];
  const now = Date.now();
  if (s && !s.ended && (now >= s.expires || now < s.lastClock || s.workerOrigin !== performance.timeOrigin || performance.now() >= s.deadline)) {
    s.enabled=false; s.ended=true; s.generation++;
  }
  if (s) s.lastClock = now;
  if (popup && message.kind === 'start') {
    if (s && !s.ended) return {ok:false};
    if (Object.keys(sessions).length >= 2 && !s) return {ok:false};
    s = {id:crypto.randomUUID(),enabled:true,ended:false,generation:1,sequence:0,expires:now+15*60*1000,lastClock:now,
         slot:Object.entries(sessions).some(([key,value])=>Number(key)!==tabId && value.slot===1)?2:1,
         workerOrigin:performance.timeOrigin,deadline:performance.now()+15*60*1000,
         events:[],dropped:0,rejected:0,rateAt:now,rateCount:0};
    sessions[tabId]=s;
  } else if (popup && s && ['pause','resume','stop'].includes(message.kind)) {
    s.generation++;
    if (message.kind === 'stop') { s.enabled=false; s.ended=true; }
    else s.enabled=message.kind==='resume' && !s.ended;
  } else if (!popup && s && message.kind === 'event') {
    const keys=Object.keys(message).sort().join(',');
    if (keys !== 'action,control_id,generation,kind,role' || !s.enabled || s.ended || message.generation !== s.generation ||
        !ACTIONS.has(message.action) || !ROLES.has(message.role) || !/^[a-f0-9]{16}$/.test(message.control_id)) s.rejected++;
    else {
      if (now-s.rateAt>=1000) { s.rateAt=now; s.rateCount=0; }
      if (++s.rateCount>20 || s.events.length>=256 || s.sequence>=1000) s.dropped++;
      else s.events.push({schema_version:1,event_id:crypto.randomUUID(),timestamp_utc:new Date(now).toISOString(),
        device_id:'laboratorio-sintetico',session_id:s.id,app:'synthetic-web',event_type:'browser_action',action:message.action,
        target:message.role+'-'+message.control_id,duration_ms:0,screenshot_ref:null,
        metadata:{category:'synthetic',control_role:message.role,source_sequence:++s.sequence}});
    }
  } else if (popup && ['bridge_ticket','bridge_export','bridge_ack'].includes(message.kind)) {
    const result=await bridgeMessage(message.kind,s,message);
    if(s){sessions[tabId]=s;await chrome.storage.session.set({sessions});}
    return result;
  } else if (!['status','export'].includes(message.kind)) return {ok:false};
  if (s) { sessions[tabId]=s; await chrome.storage.session.set({sessions}); }
  if (popup && message.kind === 'export') return {ok:true,report:{schema_version:1,kind:'synthetic_web_extension',capture_real:false,pilot_authorized:false,
    events:s?.events || [],dropped:s?.dropped || 0,rejected:s?.rejected || 0}};
  return {ok:true,enabled:!!s?.enabled,ended:!!s?.ended,generation:s?.generation || 0,
          remainingMs:s && s.workerOrigin===performance.timeOrigin ? Math.max(0,Math.min(s.expires-now,s.deadline-performance.now())) : 0,
          count:s?.events.length || 0,dropped:s?.dropped || 0};
}
chrome.runtime.onMessage.addListener((message,sender,respond)=>{
  chain=chain.then(()=>handle(message,sender)).catch(()=>({ok:false}));
  chain.then(respond); return true;
});
chrome.tabs.onRemoved.addListener(tabId=>{
  chain=chain.then(async()=>{const data=await chrome.storage.session.get('sessions');if(data.sessions){delete data.sessions[tabId];await chrome.storage.session.set(data);}}).catch(()=>{});
});
