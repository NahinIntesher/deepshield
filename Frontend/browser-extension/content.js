'use strict';
/* On-page banner. The model never reads a page's Real/Fake labels.
   Content scripts cannot call the model with an unauthenticated user.
   A toolbar click grants captureVisibleTab permission; no silent full-screen capture. */
(()=>{
 if(window.__deepShieldLoaded)return;window.__deepShieldLoaded=true;
 const source=location.hostname.includes('youtube')||location.hostname==='youtu.be'?'YouTube':location.hostname.includes('instagram')?'Instagram':'Facebook';
 let enabled=false,manualVisible=false,scanning=false,lastKey='',lastScan=0,activeVideo=null,lastResult='',lastKind='neutral';
 const root=document.createElement('div');root.id='ds-extension-overlay-root';
 root.style.cssText='position:fixed;z-index:2147483647;top:12px;left:12px;pointer-events:none;display:none';
 const shadow=root.attachShadow({mode:'closed'});
 const style=document.createElement('style');style.textContent=`
   .bubble{display:flex;align-items:center;gap:10px;border-radius:12px;padding:11px 13px;background:#0a2633;color:#efffff;border:1px solid #417281;box-shadow:0 12px 32px #00151c6e;font:600 12px/1.4 system-ui,sans-serif;pointer-events:auto;max-width:340px}
   .dot{width:8px;height:8px;border-radius:50%;background:#7ee2ca;flex-shrink:0}.bubble.real .dot{background:#32e3ae}.bubble.fake .dot{background:#ff6476}.bubble.warning .dot{background:#fac978}
   button{font:700 11px system-ui,sans-serif;color:#122b32;background:#a3ffe0;border:0;border-radius:8px;padding:7px 9px;cursor:pointer}
   .small{font-size:10px;color:#b4d5dd;font-weight:400;margin-top:2px}
 `;shadow.appendChild(style);
 const bubble=document.createElement('div');bubble.className='bubble';
 const dot=document.createElement('div');dot.className='dot';
 const label=document.createElement('div');label.innerHTML='<div>DeepShield · Ready</div><div class="small">Tap to analyze visible video</div>';
 const button=document.createElement('button');button.textContent='Scan';button.addEventListener('click',()=>void scan());
 bubble.append(dot,label,button);shadow.appendChild(bubble);document.documentElement.appendChild(root);
 function show(message,sub,kind='neutral'){
   lastResult=message;lastKind=kind;label.textContent='';
   const title=document.createElement('div');title.textContent=message;
   const desc=document.createElement('div');desc.className='small';desc.textContent=sub;
   label.append(title,desc);bubble.className='bubble '+kind;
   button.textContent=scanning?'Working…':'Scan';button.disabled=scanning;
   position();
 }
 function position(){if(!enabled&&!scanning&&!manualVisible){root.style.display='none';return}const v=activeVideo||findVideo();if(!v){root.style.display='none';return}
   const b=v.getBoundingClientRect();if(b.width<180||b.height<100||b.bottom<20||b.top>innerHeight){root.style.display='none';return}
   root.style.display='block';root.style.left=`${Math.min(innerWidth-320,Math.max(8,b.left+10))}px`;root.style.top=`${Math.max(8,b.top+12)}px`;
 }
 function findVideo(){return [...document.querySelectorAll('video')].filter(v=>{
  const b=v.getBoundingClientRect();return b.width>220&&b.height>125&&b.bottom>0&&b.top<innerHeight&&getComputedStyle(v).visibility!=='hidden';
 }).sort((a,b)=>(Number(!a.paused)-Number(!b.paused))*-100000+(b.clientWidth*b.clientHeight)-(a.clientWidth*a.clientHeight))[0]||null}
 const sleep=t=>new Promise(resolve=>setTimeout(resolve,t));
 function frame(){return new Promise((resolve,reject)=>chrome.runtime.sendMessage({type:'CAPTURE_FRAME'},r=>{
   if(chrome.runtime.lastError)return reject(new Error(chrome.runtime.lastError.message));
   if(r?.error)return reject(new Error(r.error));
   resolve(r.dataUrl);
 }));}
 function analyze(base64){return new Promise((resolve,reject)=>chrome.runtime.sendMessage({type:'ANALYZE_CAPTURE',base64,source},r=>{
  if(chrome.runtime.lastError)return reject(new Error(chrome.runtime.lastError.message));
  if(r?.error)return reject(new Error(r.error));resolve(r.result);
 }));}
 async function scan(){
  if(scanning)return;const v=findVideo();if(!v){show('No visible video','Play a video before starting a scan','warning');return}
  if(v.paused){show('Video is paused','Play the video, then scan','warning');return}
  activeVideo=v;scanning=true;lastScan=Date.now();show('Analyzing on-screen video','Keep this tab open while 16 frames are captured');
  const rect=v.getBoundingClientRect();const visible={x:Math.max(0,rect.left),y:Math.max(0,rect.top),w:Math.min(innerWidth,rect.right)-Math.max(0,rect.left),h:Math.min(innerHeight,rect.bottom)-Math.max(0,rect.top)};
  if(visible.w<180||visible.h<110){scanning=false;show('Video not visible enough','Scroll until most of the video is in view','warning');return}
  const canvas=document.createElement('canvas');const ratio=Math.min(1,960/visible.w);canvas.width=Math.max(2,Math.round(visible.w*ratio));canvas.height=Math.max(2,Math.round(visible.h*ratio));const context=canvas.getContext('2d');
  let stream=null,recorder=null;
  try{
   if(!window.MediaRecorder||!canvas.captureStream)throw new Error('Video recording is not supported by this browser');
   stream=canvas.captureStream(6);
   const format=MediaRecorder.isTypeSupported('video/webm;codecs=vp8')?'video/webm;codecs=vp8':'video/webm';
   const chunks=[];recorder=new MediaRecorder(stream,{mimeType:format,videoBitsPerSecond:1100000});
   recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
   const stopped=new Promise((resolve,reject)=>{recorder.onstop=resolve;recorder.onerror=e=>reject(new Error('Recording failed'))});
   recorder.start(1000);
   for(let i=0;i<16;i++){
    if(!document.contains(v)||document.hidden||v.paused)throw new Error('Scanning stopped: keep the video visible and playing');
    root.style.visibility='hidden';
    const screenshot=await frame();
    const image=new Image();image.src=screenshot;await image.decode();
    const sx=image.naturalWidth/innerWidth,sy=image.naturalHeight/innerHeight;
    context.drawImage(image,visible.x*sx,visible.y*sy,visible.w*sx,visible.h*sy,0,0,canvas.width,canvas.height);
    root.style.visibility='visible';
    if(i===0)show('Capturing video frames','Collecting visible frames for analysis');
    await sleep(900);
   }
   recorder.stop();await stopped;stream.getTracks().forEach(t=>t.stop());stream=null;
   const blob=new Blob(chunks,{type:'video/webm'});
   if(blob.size<512)throw new Error('Recording was empty');
   show('Running trained detector','Analysis may take several seconds');
   const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error('Capture encoding failed'));reader.readAsDataURL(blob)});
   const result=await analyze(dataUrl.split(',')[1]);
   const isFake=String(result.verdict).toLowerCase()==='fake';
   show(isFake?'Likely manipulated':'Model predicts real',`Model score ${Number(result.confidence_percentage).toFixed(1)}% · not proof`,isFake?'fake':'real');
   lastKey=`${location.href}|${v.currentSrc}|${Math.floor(v.duration||0)}`;
  }catch(e){show('Could not analyze video',String(e.message||e).slice(0,110),'warning')}
  finally{root.style.visibility='visible';if(recorder?.state==='recording')recorder.stop();stream?.getTracks().forEach(t=>t.stop());scanning=false;button.disabled=false;button.textContent='Rescan';}
 }
 function update(){if(!enabled||scanning)return;activeVideo=findVideo();position();
   if(!activeVideo)return;
   const key=`${location.href}|${activeVideo.currentSrc}|${Math.floor(activeVideo.duration||0)}`;
   if(key!==lastKey&&Date.now()-lastScan>12000&& !activeVideo.paused){lastKey=key;void scan()}
 }
 let observerTimer;const observer=new MutationObserver(()=>{clearTimeout(observerTimer);observerTimer=setTimeout(update,500)});
 observer.observe(document.documentElement,{subtree:true,childList:true});window.addEventListener('scroll',position,{passive:true});window.addEventListener('resize',position,{passive:true});
 chrome.runtime.onMessage.addListener((msg,sender,reply)=>{
  if(msg.type==='ENABLE'){enabled=!!msg.enabled;activeVideo=findVideo();if(enabled){manualVisible=false;show('DeepShield is ready','Auto-scan is enabled for this tab');setTimeout(update,500)}else{manualVisible=false;position()}reply({ok:true});}
  if(msg.type==='SCAN_NOW'){manualVisible=true;activeVideo=findVideo();void scan();reply({ok:true});}
  if(msg.type==='GET_CONTENT_STATE')reply({enabled,scanning,lastResult});
 });
 chrome.runtime.sendMessage({type:'GET_TAB_STATE'},r=>{if(r?.enabled){enabled=true;update()}});
 setInterval(update,2800);
})();
