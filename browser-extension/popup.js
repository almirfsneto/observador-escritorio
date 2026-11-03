'use strict';
let tabId;
const status=document.getElementById('status');
chrome.tabs.query({active:true,currentWindow:true}).then(tabs=>{tabId=tabs[0]?.id;refresh();});
async function request(kind){
  try{return await chrome.runtime.sendMessage({kind,tabId});}catch{return {ok:false};}
}
async function refresh(){const s=await request('status');status.textContent=!s.ok?'Origem não permitida':s.ended?'ENCERRADO':s.enabled?'ATIVO | '+s.count+' eventos':'PAUSADO/DESATIVADO';}
for(const kind of ['start','pause','resume','stop'])document.getElementById(kind).addEventListener('click',async()=>{await request(kind);refresh();});
document.getElementById('export').addEventListener('click',async()=>{
  const result=await request('export');if(!result.ok)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(result.report,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='aceite-web-sintetico.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
