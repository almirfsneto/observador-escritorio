'use strict';
(() => {
  if (location.origin !== 'http://127.0.0.1:8765' || !location.pathname.startsWith('/synthetic-lab/') ||
      document.querySelector('meta[name="observador-synthetic-lab"]')?.content !== 'v1' || window !== window.top) return;
  const actions=new Set(['save','review','download','rename','move','register','open_menu','select_menu','select_tab','submit','navigate']);
  const roles=new Set(['button','menuitem','tab','window','control']);
  let state={enabled:false,generation:0}, deadline=0, transitionSent=false;
  const identities=new WeakMap();
  const banner=document.createElement('div');
  banner.id='observador-lab-status';
  banner.setAttribute('role','status');
  banner.style.cssText='position:fixed;bottom:0;left:0;z-index:2147483647;background:#142d42;color:white;padding:10px;font:14px sans-serif';
  document.documentElement.append(banner);
  function identity(element){if(!identities.has(element))identities.set(element,crypto.randomUUID().replaceAll('-','').slice(0,16));return identities.get(element);}
  function emit(action,role,element){
    if(!state.enabled || performance.now()>=deadline)return;
    chrome.runtime.sendMessage({kind:'event',generation:state.generation,action,role,control_id:identity(element)}).catch(()=>{});
  }
  async function refresh(){
    try {
      const next=await chrome.runtime.sendMessage({kind:'status'});
      if(!next?.ok){state.enabled=false;banner.textContent='LAB WEB — DESATIVADO';return;}
      state=next; deadline=performance.now()+next.remainingMs;
      banner.textContent='LAB WEB — '+(next.ended?'ENCERRADO':next.enabled?'ATIVO':'PAUSADO/DESATIVADO')+' | eventos: '+next.count+' | perdas: '+next.dropped;
      if(next.enabled && !transitionSent){transitionSent=true;emit('transition','window',document.documentElement);}
    }catch{state.enabled=false;banner.textContent='LAB WEB — INDISPONÍVEL';}
  }
  function interaction(event){
    if(!event.isTrusted || !(event.target instanceof Element))return;
    if(event.target.closest('input,textarea,[contenteditable]'))return;
    const element=event.target.closest('[data-observador-action]');
    if(!element)return;
    const action=element.getAttribute('data-observador-action'),role=element.getAttribute('data-observador-role');
    if(!actions.has(action)||!roles.has(role))return;
    if((event.type==='submit') !== (action==='submit'))return;
    emit(action,role,element);
  }
  document.addEventListener('click',interaction,true);
  document.addEventListener('submit',interaction,true);
  window.addEventListener('popstate',()=>emit('transition','window',document.documentElement));
  window.addEventListener('hashchange',()=>emit('transition','window',document.documentElement));
  refresh(); setInterval(refresh,250);
})();
