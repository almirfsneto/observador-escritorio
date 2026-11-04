'use strict';
// File-only lab handshake. No nativeMessaging, sockets, fetch or extra permission.
const exactKeys=(value,keys)=>value && typeof value==='object' && !Array.isArray(value) && Object.keys(value).sort().join(',')===keys.slice().sort().join(',');
const bridgeUuid=value=>typeof value==='string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
const bridgeInt=(value,min=1,max=Number.MAX_SAFE_INTEGER)=>Number.isSafeInteger(value)&&value>=min&&value<=max;
const canonicalBridge=value=>JSON.stringify(sortBridge(value));
function sortBridge(value){if(Array.isArray(value))return value.map(sortBridge);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,sortBridge(value[key])]));return value;}
async function bridgeDigest(value){const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonicalBridge(value)));return [...new Uint8Array(bytes)].map(v=>v.toString(16).padStart(2,'0')).join('');}
async function bridgeMessage(kind,s,message){
  if(!s)return {ok:false};
  if(kind==='bridge_ticket'){
    const t=message.document;
    if(!exactKeys(t,['schema_version','kind','bridge_epoch','generation','source','next_batch_sequence','next_source_sequence','remaining_ms']) || t.schema_version!==1 || t.kind!=='synthetic_bridge_ticket' ||
       !bridgeUuid(t.bridge_epoch)||!bridgeInt(t.generation)||!bridgeInt(t.next_batch_sequence)||!bridgeInt(t.next_source_sequence)||!bridgeInt(t.remaining_ms,1,900000)||
       !exactKeys(t.source,['kind','version','instance','origin','tab_slot'])||t.source.kind!=='web'||t.source.version!==1||t.source.instance!==s.id||
       t.source.origin!=='http://127.0.0.1:8765'||t.source.tab_slot!==s.slot)return {ok:false};
    if(!s.enabled||s.ended)return {ok:false};
    const old=s.bridge;
    // Re-ticketing after control invalidates unsent data, rather than replaying across pause.
    const first=s.events.findIndex(e=>e.metadata.source_sequence>=t.next_source_sequence);
    const cursor=old ? s.events.length : first<0?s.events.length:first;
    if(old&&old.ticket.bridge_epoch===t.bridge_epoch&&old.ticket.generation>=t.generation)return {ok:false};
    s.bridge={ticket:t,cursor,pending:null,nextBatch:t.next_batch_sequence,deadline:performance.now()+t.remaining_ms};
    return {ok:true};
  }
  const b=s.bridge;
  if(!b)return {ok:false};
  if(kind==='bridge_export'){
    if(b.pending)return {ok:true,batch:b.pending};
    if(!s.enabled||s.ended||performance.now()>=b.deadline)return {ok:false};
    const events=s.events.slice(b.cursor,b.cursor+100);
    if(!events.length)return {ok:false};
    b.pending={schema_version:1,kind:'synthetic_source_batch',bridge_epoch:b.ticket.bridge_epoch,generation:b.ticket.generation,
               batch_sequence:b.nextBatch,batch_id:crypto.randomUUID(),source:b.ticket.source,events};
    return {ok:true,batch:b.pending};
  }
  if(kind==='bridge_ack'){
    const a=message.document,p=b.pending;
    if(!p||!exactKeys(a,['schema_version','kind','bridge_epoch','generation','batch_sequence','batch_id','source_instance','digest',
       'accepted_count','written_count','source_gap_count','source_last_sequence','scope','status'])||a.schema_version!==1||a.kind!=='synthetic_bridge_ack'||
       a.bridge_epoch!==p.bridge_epoch||a.generation!==p.generation||a.batch_sequence!==p.batch_sequence||a.batch_id!==p.batch_id||
       a.source_instance!==s.id||a.accepted_count!==p.events.length||a.written_count!==p.events.length||!bridgeInt(a.source_gap_count,0)||
       a.source_last_sequence!==p.events[p.events.length-1].metadata.source_sequence||a.digest!==await bridgeDigest(p)||
       a.scope!=='durable_local_inbox_not_business_completion'||a.status!=='committed')return {ok:false};
    b.cursor+=p.events.length;b.nextBatch++;b.pending=null;
    return {ok:true};
  }
  return {ok:false};
}
