'use strict';
/* All API tokens remain in the extension service worker / extension storage,
   never injected into the social media page. */
const API='http://localhost:8000';
function errorText(data){return typeof data?.detail==='string'?data.detail:'The DeepShield server did not accept this request.'}
function storageGet(key){return new Promise(resolve=>chrome.storage.local.get(key,resolve))}
function sessionGet(key){return new Promise(resolve=>chrome.storage.session.get(key,resolve))}
function sessionSet(data){return new Promise(resolve=>chrome.storage.session.set(data,resolve))}
async function checkToken(token){
 const r=await fetch(`${API}/api/integrations/extension/status`,{headers:{Authorization:`Bearer ${token}`}});
 const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(errorText(data));return data;
}
async function uploadCapture(message){
 const {token}=await storageGet('token');
 if(!token)throw new Error('Connect your DeepShield account from the extension popup first.');
 const raw=atob(message.base64);
 const bytes=new Uint8Array(raw.length);
 for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
 const body=new FormData();body.append('file',new Blob([bytes],{type:'video/webm'}),'visible-capture.webm');
 const params=new URLSearchParams({source:message.source});
 const response=await fetch(`${API}/api/integrations/extension/analyze?${params}`,{
   method:'POST',headers:{Authorization:`Bearer ${token}`},body
 });
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(errorText(data));
 return {verdict:data.verdict,confidence_percentage:data.confidence_percentage,detection_id:data.detection_id,model_id:data.model_id};
}
chrome.runtime.onMessage.addListener((message,sender,respond)=>{
 if(message.type==='CAPTURE_FRAME'){
   if(!sender.tab?.windowId){respond({error:'Missing source tab'});return false}
   chrome.tabs.captureVisibleTab(sender.tab.windowId,{format:'jpeg',quality:82},dataUrl=>{
     const failure=chrome.runtime.lastError;
     respond(failure?{error:failure.message}:{dataUrl});
   });return true;
 }
 if(message.type==='ANALYZE_CAPTURE'){
   uploadCapture(message).then(result=>respond({ok:true,result})).catch(e=>respond({error:e.message}));return true;
 }
 if(message.type==='GET_TAB_STATE'){
   sessionGet('enabledTabs').then(data=>respond({enabled:!!(data.enabledTabs||{})[sender.tab?.id]}));return true;
 }
 if(message.type==='SET_TAB_STATE'){
   sessionGet('enabledTabs').then(async data=>{
     const entries=data.enabledTabs||{};entries[message.tabId]=!!message.enabled;
     await sessionSet({enabledTabs:entries});return {enabled:!!message.enabled};
   }).then(respond).catch(e=>respond({error:e.message}));return true;
 }
 if(message.type==='TOKEN_TEST'){
   checkToken(message.token).then(data=>respond({ok:true,data})).catch(e=>respond({error:e.message}));return true;
 }
 return false;
});
chrome.tabs.onRemoved.addListener(id=>{
 sessionGet('enabledTabs').then(d=>{const entries=d.enabledTabs||{};delete entries[id];return sessionSet({enabledTabs:entries})}).catch(()=>{});
});
