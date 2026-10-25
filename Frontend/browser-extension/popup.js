'use strict';
const $=id=>document.getElementById(id);
const send=message=>new Promise((resolve,reject)=>chrome.runtime.sendMessage(message,r=>chrome.runtime.lastError?reject(new Error(chrome.runtime.lastError.message)):resolve(r)));
const sendTab=(id,message)=>new Promise((resolve,reject)=>chrome.tabs.sendMessage(id,message,r=>chrome.runtime.lastError?reject(new Error('Open a supported video website and reload the page.')):resolve(r)));
let tabId=null,connected=false;
function notify(s){$('message').textContent=s}
function status(ok,text,caption){connected=ok;$('status-light').className='light'+(ok?' on':'');$('status-title').textContent=text;$('status-caption').textContent=caption;$('scan').disabled=!ok}
async function init(){
 const tabs=await chrome.tabs.query({active:true,currentWindow:true});tabId=tabs[0]?.id;
 const saved=await chrome.storage.local.get('token');
 if(saved.token){try{const result=await send({type:'TOKEN_TEST',token:saved.token});if(!result.ok)throw new Error(result.error);status(true,'Connected · '+result.data.user,`${result.data.remaining} / ${result.data.limit} scans left today`)}catch(e){status(false,'Could not reach the local server',e.message)}}
 if(tabId!=null){const stored=await chrome.storage.session.get('enabledTabs');$('enable').checked=!!(stored.enabledTabs||{})[tabId]}
}
$('connect').addEventListener('click',async()=>{
 const token=$('token').value.trim();if(!token.startsWith('dsx_')){notify('Paste the token shown on your DeepShield extension settings page.');return}
 try{const result=await send({type:'TOKEN_TEST',token});if(!result.ok)throw new Error(result.error);await chrome.storage.local.set({token});$('token').value='';status(true,'Connected · '+result.data.user,`${result.data.remaining} / ${result.data.limit} scans left today`);notify('Connected successfully. Enable scanning for this tab.')}catch(e){notify(e.message)}
});
$('disconnect').addEventListener('click',async()=>{await chrome.storage.local.remove('token');status(false,'Disconnected','Your browser token was cleared.');notify('For full revocation, use the DeepShield website.');$('enable').checked=false;if(tabId!=null){await send({type:'SET_TAB_STATE',tabId,enabled:false});sendTab(tabId,{type:'ENABLE',enabled:false}).catch(()=>{})}});
$('enable').addEventListener('change',async e=>{
 if(!connected){e.target.checked=false;notify('Connect to the backend first.');return}
 if(tabId==null){e.target.checked=false;notify('No active browser tab.');return}
 try{await send({type:'SET_TAB_STATE',tabId,enabled:e.target.checked});await sendTab(tabId,{type:'ENABLE',enabled:e.target.checked});notify(e.target.checked?'Auto-scanning enabled in this tab. Keep the video playing.':'Auto-scanning disabled.')}catch(ex){e.target.checked=false;await send({type:'SET_TAB_STATE',tabId,enabled:false}).catch(()=>{});notify(ex.message)}
});
$('scan').addEventListener('click',async()=>{if(!connected||tabId==null)return;try{await sendTab(tabId,{type:'SCAN_NOW'});notify('Video scan started. Check the on-page status indicator.')}catch(e){notify(e.message)}});
init().catch(e=>notify(e.message));
