package bd.com.nahin.deepshield_mobile

import android.app.*
import android.content.*
import android.content.pm.ServiceInfo
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.view.*
import android.widget.*
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import kotlin.math.*

/** Explicit session only: no boot receiver, accessibility service, audio, or disk capture. */
class LiveGuardService : Service() {
    companion object { @Volatile var snapshot: Map<String, Any?> = mapOf("running" to false, "phase" to "off") }
    private val main = Handler(Looper.getMainLooper())
    private lateinit var captureThread: HandlerThread
    private lateinit var capture: Handler
    private val network = Executors.newSingleThreadExecutor()
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var window: WindowManager? = null
    private var panel: LinearLayout? = null
    private var statusText: TextView? = null
    private var detailText: TextView? = null
    private var counterText: TextView? = null
    private var pauseButton: Button? = null
    private var layout: WindowManager.LayoutParams? = null
    private val frames = ArrayList<ByteArray>()
    private var previous: IntArray? = null
    private var width = 576; private var height = 1280
    @Volatile private var active = false
    @Volatile private var paused = false
    @Volatile private var busy = false
    @Volatile private var visible = true
    @Volatile private var generation = 0
    @Volatile private var connection: HttpURLConnection? = null
    private var nextSample = 0L; private var nextScan = 0L
    private var used = 0; private var budget = 3; private var interval = 120
    private var automatic = true; private var requested = true
    private var language = "en"; private var source = "Other"
    private var allowedSources = emptySet<String>()
    private var otherPackage: String? = null
    private var foregroundPackage: String? = null
    private var capturePackage: String? = null
    @Volatile private var insideAllowedApp = false
    private var lastAlertRevision = Int.MIN_VALUE
    private var apiBase = ""; private var token = ""
    private var resultId: Int? = null
    private var resultTime = 0L
    private var collapsed = true
    private fun font():Typeface = try { Typeface.createFromAsset(assets,if(language=="bn")"flutter_assets/assets/fonts/BalooDa2.ttf" else "flutter_assets/assets/fonts/Quicksand.ttf") } catch(_:Exception) {Typeface.DEFAULT}
    private fun t(en: String, bn: String) = if (language == "bn") bn else en
    private fun dp(value: Int) = (value * resources.displayMetrics.density).roundToInt()
    override fun onBind(intent: Intent?) = null
    override fun onCreate() { super.onCreate(); captureThread = HandlerThread("DeepShieldCapture").apply { start() }; capture = Handler(captureThread.looper) }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "stop" -> { stopSelf(); return START_NOT_STICKY }
            "pause" -> { setPaused(true); return START_NOT_STICKY }
            "resume" -> { setPaused(false); return START_NOT_STICKY }
            "scan" -> { if (active && !paused && !busy && used < budget) { requested = true; nextScan = 0 }; return START_NOT_STICKY }
        }
        if (active || intent == null || !intent.hasExtra("permission")) { if (!active) stopSelf(); return START_NOT_STICKY }
        language = intent.getStringExtra("language") ?: "en"; source = intent.getStringExtra("source") ?: "Other"
        allowedSources = intent.getStringArrayListExtra("allowedSources")?.toSet() ?: emptySet()
        otherPackage = intent.getStringExtra("otherPackage")
        apiBase = intent.getStringExtra("apiBase") ?: ""; token = intent.getStringExtra("token") ?: ""
        budget = intent.getIntExtra("budget", 3).coerceIn(1,100); interval = intent.getIntExtra("interval",120).coerceIn(60,600)
        automatic = intent.getBooleanExtra("automatic",true);requested=automatic;nextScan=SystemClock.elapsedRealtime()+5000
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel("live_guard", "DeepShield Live Guard", NotificationManager.IMPORTANCE_LOW))
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel("deepfake_alerts", t("Possible deepfake alerts", "সম্ভাব্য ডিপফেকের সতর্কতা"), NotificationManager.IMPORTANCE_HIGH).apply { description=t("Warnings for Fake results only, on the selected video.","শুধু বেছে নেওয়া ভিডিওতে নকল হওয়ার ফল এলে সতর্ক করে।") })
        val notification = notification(t("Screen sharing active", "স্ক্রিন শেয়ারিং চলছে"))
        if (Build.VERSION.SDK_INT >= 29) startForeground(601, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION) else startForeground(601, notification)
        try {
            val permission = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra("permission",Intent::class.java) else @Suppress("DEPRECATION") intent.getParcelableExtra<Intent>("permission")
            projection = getSystemService(MediaProjectionManager::class.java).getMediaProjection(intent.getIntExtra("resultCode", Activity.RESULT_CANCELED),permission!!)
            projection!!.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() { main.post { stopSelf() } }
                override fun onCapturedContentResize(w: Int,h: Int) { capture.post { resize(w,h) } }
                override fun onCapturedContentVisibilityChanged(isVisible: Boolean) { visible=isVisible; if(!isVisible) { generation++;resultId=null;clearWarning(); capture.post { frames.clear(); previous=null }; update("hidden",t("Shared app is not visible", "শেয়ার করা অ্যাপ দেখা যাচ্ছে না"),t("Return to the app you selected.","বেছে নেওয়া অ্যাপে ফিরুন।")) } }
            },main)
            val metrics = resources.displayMetrics
            val size = if (Build.VERSION.SDK_INT >= 30) getSystemService(WindowManager::class.java).maximumWindowMetrics.bounds else Rect(0,0,metrics.widthPixels,metrics.heightPixels)
            dimensions(size.width(),size.height()); createReader()
            display = projection!!.createVirtualDisplay("DeepShield opt-in Live Guard",width,height,metrics.densityDpi,DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,reader!!.surface,null,capture)
            active=true; showPanel(); update("ready",t("Live Guard is on", "Live Guard চালু"),t("Open $source and stay on one video for 8 seconds.","$source খুলে একটি ভিডিও অন্তত ৮ সেকেন্ড দেখুন।"))
        } catch (_:Exception) { update("error",t("Could not start screen sharing", "স্ক্রিন শেয়ারিং শুরু হয়নি"),t("Open DeepShield and try again.","DeepShield খুলে আবার চেষ্টা করুন।"));stopSelf() }
        return START_NOT_STICKY
    }
    private fun dimensions(w:Int,h:Int) { val scale=min(1.0,1280.0/max(w,h).coerceAtLeast(1));width=max(112,(w*scale).toInt()/2*2);height=max(112,(h*scale).toInt()/2*2) }
    private fun resize(w:Int,h:Int) { if(!active)return; dimensions(w,h); display?.surface=null;reader?.close();createReader();display?.resize(width,height,resources.displayMetrics.densityDpi);display?.surface=reader!!.surface;frames.clear();previous=null;generation++ }
    private fun createReader() { reader=ImageReader.newInstance(width,height,PixelFormat.RGBA_8888,2);reader!!.setOnImageAvailableListener({ r ->
        val image=try { r.acquireLatestImage() } catch (_:Exception) { null } ?: return@setOnImageAvailableListener
        try {
            val now=SystemClock.elapsedRealtime()
            if(!active||!visible||now<nextSample)return@setOnImageAvailableListener
            nextSample=now+500
            if(!allowedForeground(now)||paused)return@setOnImageAvailableListener
            val plane=image.planes[0];val padded=width+(plane.rowStride-plane.pixelStride*width)/plane.pixelStride
            val raw=Bitmap.createBitmap(padded,height,Bitmap.Config.ARGB_8888);raw.copyPixelsFromBuffer(plane.buffer)
            val bitmap=Bitmap.createBitmap(raw,0,0,width,height);if(bitmap!==raw)raw.recycle()
            try { processFrame(bitmap,now) } finally { bitmap.recycle() }
        } catch (_:Exception) { frames.clear(); previous=null } finally { image.close() }
    },capture) }
    private fun clearWarning() { main.post { getSystemService(NotificationManager::class.java).cancel(602) } }
    private fun allowedForeground(now:Long):Boolean {
        foregroundPackage=try {AppAccess.foreground(this,foregroundPackage)}catch(_:Exception){null}
        val selected=if(getSystemService(KeyguardManager::class.java).isKeyguardLocked)null else LiveGuardPolicy.sourceFor(foregroundPackage,allowedSources,otherPackage)
        if(selected==null){
            if(insideAllowedApp||frames.isNotEmpty()||resultId!=null){generation++;frames.clear();previous=null;resultId=null;clearWarning()}
            if(insideAllowedApp||snapshot["phase"]!="outside")update("outside",t("Waiting for a selected app", "বেছে দেওয়া অ্যাপের অপেক্ষায়"),t("Capture is paused outside the apps you allowed.","বেছে দেওয়া অ্যাপের বাইরে কোনো ছবি নেওয়া হচ্ছে না।"))
            insideAllowedApp=false;capturePackage=null;return false
        }
        if(capturePackage!=foregroundPackage){generation++;frames.clear();previous=null;resultId=null;clearWarning();nextScan=now+1000;requested=automatic;capturePackage=foregroundPackage}
        insideAllowedApp=true;source=selected;return true
    }
    private fun processFrame(bitmap:Bitmap,now:Long) {
        val thumb=Bitmap.createScaledBitmap(bitmap,24,24,false);val pixels=IntArray(576);thumb.getPixels(pixels,0,24,0,0,24,24);thumb.recycle()
        var brightness=0.0;var difference=0.0
        for(i in pixels.indices) { brightness+=(Color.red(pixels[i])+Color.green(pixels[i])+Color.blue(pixels[i]))/3.0;val old=previous?.get(i);if(old!=null)difference+=(abs(Color.red(pixels[i])-Color.red(old))+abs(Color.green(pixels[i])-Color.green(old))+abs(Color.blue(pixels[i])-Color.blue(old)))/3.0 }
        previous=pixels
        if(brightness/576<4) { if(frames.isNotEmpty()||resultId!=null)generation++;frames.clear();resultId=null;clearWarning();update("blank",t("No visible video", "ভিডিও দেখা যাচ্ছে না"),t("Protected or blank screens cannot be analyzed.","সুরক্ষিত বা ফাঁকা স্ক্রিন বিশ্লেষণ করা যায় না।"));return }
        if(difference/(576*255)>0.28) { generation++;frames.clear();resultId=null;clearWarning();nextScan=now+1000;requested=automatic;update("changed",t("Screen changed", "স্ক্রিন বদলেছে"),t("Stay on one video while it is sampled.","নমুনা নেওয়ার সময় একই ভিডিওতে থাকুন।"));return }
        if(resultId!=null&&now-resultTime>20000) { resultId=null;clearWarning();update("waiting",t("Waiting for next scan", "পরের স্ক্যানের অপেক্ষা"),t("Previous result is saved in History.","আগের ফল History-তে আছে।")) }
        if(busy||used>=budget||now<nextScan||(!automatic&&!requested))return
        val stream=ByteArrayOutputStream();bitmap.compress(Bitmap.CompressFormat.JPEG,75,stream)
        val bytes=stream.toByteArray();if(bytes.size !in 512..500000) { frames.clear();return }
        frames.add(bytes);update("capturing",t("Sampling video · ${frames.size}/16", "ভিডিও নেওয়া হচ্ছে · ${frames.size}/16"),t("Keep this video visible for 8 seconds.","ভিডিওটি অন্তত ৮ সেকেন্ড খোলা রাখুন।"))
        if(frames.size==16) { val batch=frames.toList();frames.clear();busy=true;requested=false;val revision=generation;val capturedSource=source;update("analyzing",t("Analyzing captured video…", "নেওয়া ভিডিও বিশ্লেষণ হচ্ছে…"),t("You can keep browsing. A changed screen clears this result.","ব্রাউজ করতে পারেন। স্ক্রিন বদলালে আগের ফল সরিয়ে দেওয়া হবে।"));network.execute { analyze(batch,revision,capturedSource) } }
    }
    private fun analyze(batch:List<ByteArray>,revision:Int,capturedSource:String) {
        var fatal=false
        try {
            val boundary="DeepShield"+java.util.UUID.randomUUID().toString().replace("-","")
            val url=URL("$apiBase/api/integrations/mobile-overlay/analyze?source=${java.net.URLEncoder.encode(capturedSource,"UTF-8")}&sample_interval_ms=500")
            val c=(url.openConnection() as HttpURLConnection).apply { requestMethod="POST";instanceFollowRedirects=false;connectTimeout=45000;readTimeout=240000;doOutput=true;setRequestProperty("Authorization","Bearer $token");setRequestProperty("Content-Type","multipart/form-data; boundary=$boundary");setChunkedStreamingMode(65536) };connection=c
            c.outputStream.buffered().use { out -> batch.forEachIndexed { i,bytes -> out.write("--$boundary\r\nContent-Disposition: form-data; name=\"frames\"; filename=\"frame_$i.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".toByteArray());out.write(bytes);out.write("\r\n".toByteArray()) };out.write("--$boundary--\r\n".toByteArray()) }
            val status=c.responseCode;val text=(if(status in 200..299)c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
            if(!active)return
            if(status in 200..299) { val result=JSONObject(text);used++;if(!paused&&generation==revision) { val verdict=result.optString("verdict");resultId=result.optInt("detection_id");resultTime=SystemClock.elapsedRealtime();if(verdict=="Fake"){update("result",t("Possible deepfake", "ভিডিওটি নকল হতে পারে"),t("Check the original before trusting or sharing. This is a model result, not proof.","বিশ্বাস বা শেয়ার করার আগে আসল ভিডিওটি খুঁজে দেখুন। মডেলের এই ফল নিশ্চিত প্রমাণ নয়।"),"Fake");alertFake(revision)}else{clearWarning();update("watching",t("Live Guard is watching", "Live Guard চালু আছে"),t("You will be alerted only for a possible deepfake. Results are in History.","সম্ভাব্য ডিপফেক হলেই সতর্ক করা হবে। বিস্তারিত ফল হিস্ট্রিতে পাবেন।"))} } else update("changed",t("Video changed · result saved", "ভিডিও বদলেছে · ফল সেভ হয়েছে"),t("Open History to inspect the earlier capture.","আগের ভিডিওর ফল History-তে দেখুন।")) }
            else { fatal=status in listOf(401,403,429);val msg=when {status==429->t("Daily scan allowance reached", "আজকের স্ক্যানের limit শেষ");status==401||status==403->t("Sign in again in DeepShield", "DeepShield-এ আবার লগইন করুন");status==503->t("Model busy · retry later", "মডেল ব্যস্ত · পরে চেষ্টা করুন");status==422||status==400->t("No usable face in this capture", "এই ভিডিওতে উপযুক্ত মুখ পাওয়া যায়নি");else->t("Analysis unavailable", "বিশ্লেষণ পাওয়া যাচ্ছে না")};update("error",msg,t("Pause or stop here. Details are available in DeepShield.","এখান থেকে Pause বা Stop করুন। DeepShield-এ বিস্তারিত দেখুন।")) }
        } catch (_:Exception) { if(active&&!paused)update("error",t("Connection interrupted", "সংযোগ বিচ্ছিন্ন হয়েছে"),t("Check your internet. No result is available for this video.","ইন্টারনেট সংযোগ দেখুন। এই ভিডিওর ফল পাওয়া যায়নি।")) }
        finally { connection?.disconnect();connection=null;busy=false;nextScan=SystemClock.elapsedRealtime()+interval*1000L;if(fatal)main.post { setPaused(true);update("limit",t("Session paused", "স্ক্যান বিরতিতে"),t("Open DeepShield to check your account or allowance.","অ্যাকাউন্ট বা স্ক্যানের সীমা দেখতে DeepShield খুলুন।")) }
            else if(used>=budget)main.post { paused=true;snapshot=snapshot+mapOf("paused" to true,"limitReached" to true);pauseButton?.isEnabled=false;detailText?.append(" "+t("Session scan limit reached. Stop sharing when finished.","এইবারের স্ক্যানের সীমা শেষ। কাজ শেষ হলে শেয়ারিং বন্ধ করুন।")) }
        }
    }
    private fun setPaused(value:Boolean) { paused=value;generation++;resultId=null;clearWarning();capture.post { frames.clear();previous=null };if(!value&&used<budget) { requested=automatic;nextScan=0 };update(if(value)"paused" else "ready",if(value)t("Live Guard paused", "Live Guard বিরতিতে")else t("Live Guard resumed", "Live Guard আবার চালু"),if(value)t("Screen sharing remains active. Stop ends it completely.","স্ক্রিন শেয়ারিং চালু আছে। পুরোপুরি বন্ধ করতে Stop করুন।")else t("Stay on one video for 8 seconds.","একই ভিডিও অন্তত ৮ সেকেন্ড দেখুন।")) }
    private fun update(phase:String,title:String,detail:String,verdict:String?=null) { snapshot=mapOf("running" to active,"phase" to phase,"title" to title,"detail" to detail,"used" to used,"budget" to budget,"paused" to paused,"resultId" to resultId,"source" to source,"verdict" to verdict);main.post { statusText?.text=title;detailText?.text=detail;counterText?.text="$source · $used/$budget";pauseButton?.text=if(paused)t("Resume","চালু")else t("Pause","বিরতি");statusText?.setTextColor(when(verdict){"Fake"->Color.rgb(255,172,158);"Real"->Color.rgb(129,213,170);else->Color.WHITE});if(active)getSystemService(NotificationManager::class.java).notify(601,notification(if(paused)t("Screen sharing paused", "স্ক্রিন শেয়ারিং বিরতিতে")else t("Screen sharing active", "স্ক্রিন শেয়ারিং চলছে"))) } }
    private fun notification(text:String):Notification { val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE);val stop=PendingIntent.getService(this,1,Intent(this,LiveGuardService::class.java).setAction("stop"),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE);val builder=if(Build.VERSION.SDK_INT>=26)Notification.Builder(this,"live_guard")else @Suppress("DEPRECATION")Notification.Builder(this);return builder.setOnlyAlertOnce(true).setSmallIcon(android.R.drawable.ic_lock_lock).setContentTitle("DeepShield Live Guard").setContentText(text).setContentIntent(open).setOngoing(true).setCategory(Notification.CATEGORY_SERVICE).addAction(Notification.Action.Builder(null,t("Stop sharing","শেয়ারিং বন্ধ"),stop).build()).build() }
    private fun alertFake(revision:Int) { main.post {
        if(!active||!insideAllowedApp||!LiveGuardPolicy.shouldAlert("Fake",revision,generation,paused,lastAlertRevision))return@post
        lastAlertRevision=revision
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)return@post
        val open=PendingIntent.getActivity(this,2,Intent(this,MainActivity::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val b=if(Build.VERSION.SDK_INT>=26)Notification.Builder(this,"deepfake_alerts")else @Suppress("DEPRECATION")Notification.Builder(this)
        getSystemService(NotificationManager::class.java).notify(602,b.setSmallIcon(android.R.drawable.ic_dialog_alert).setContentTitle(t("Possible deepfake", "ভিডিওটি নকল হতে পারে")).setContentText(t("Check the original before trusting or sharing.","বিশ্বাস বা শেয়ার করার আগে আসল ভিডিওটি খুঁজে দেখুন।")).setStyle(Notification.BigTextStyle().bigText(t("The model flagged the captured video. This is not proof. Open DeepShield to inspect the result.","নেওয়া ভিডিওটি মডেলের কাছে সন্দেহজনক মনে হয়েছে। এটি নিশ্চিত প্রমাণ নয়। বিস্তারিত দেখতে DeepShield খুলুন।"))).setContentIntent(open).setAutoCancel(true).setPriority(Notification.PRIORITY_HIGH).apply { if(Build.VERSION.SDK_INT>=26)setTimeoutAfter(20000) else main.postDelayed({if(lastAlertRevision==revision)getSystemService(NotificationManager::class.java).cancel(602)},20000) }.setCategory(Notification.CATEGORY_RECOMMENDATION).build())
    } }
    private fun showPanel() {
        window=getSystemService(WindowManager::class.java)
        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(14),dp(10),dp(14),dp(10));background=GradientDrawable().apply { setColor(Color.rgb(25,28,27));cornerRadius=dp(18).toFloat();setStroke(dp(1),Color.rgb(77,95,84)) };elevation=dp(8).toFloat() }
        panel=root
        val heading=TextView(this).apply { text="◉ Live Guard";typeface=font();textSize=14f;setTextColor(Color.rgb(129,213,170));setPadding(0,0,0,dp(8));contentDescription=t("Drag to move the floating panel","প্যানেল সরাতে ধরে টানুন") }
        val header=LinearLayout(this).apply {orientation=LinearLayout.HORIZONTAL}
        header.addView(heading,LinearLayout.LayoutParams(0,dp(48),1f))
        val toggle=Button(this).apply {text="⌄";textSize=22f;minWidth=0;setPadding(0,0,0,0);setTextColor(Color.WHITE);setBackgroundColor(Color.TRANSPARENT);contentDescription=t("Expand panel","প্যানেল বড় করুন")}
        header.addView(toggle,LinearLayout.LayoutParams(dp(48),dp(48)))
        val close=Button(this).apply {text="×";textSize=24f;minWidth=0;setPadding(0,0,0,0);setTextColor(Color.WHITE);setBackgroundColor(Color.TRANSPARENT);contentDescription=t("Stop screen sharing","স্ক্রিন শেয়ারিং বন্ধ করুন");setOnClickListener {stopSelf()}}
        header.addView(close,LinearLayout.LayoutParams(dp(48),dp(48)));root.addView(header)
        statusText=TextView(this).apply { textSize=17f;setTextColor(Color.WHITE);typeface=Typeface.create(font(),Typeface.BOLD);maxLines=2;ellipsize=android.text.TextUtils.TruncateAt.END };root.addView(statusText)
        detailText=TextView(this).apply { typeface=font();textSize=13f;setTextColor(Color.rgb(205,216,208));setPadding(0,dp(6),0,dp(8)) };root.addView(detailText)
        counterText=TextView(this).apply { typeface=font();textSize=12f;setTextColor(Color.rgb(180,195,185)) };root.addView(counterText)
        val actions=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
        fun button(label:String,action:()->Unit):Button { val b=Button(this).apply { text=label;typeface=font();textSize=12f;isAllCaps=false;minWidth=0;minimumHeight=dp(48);setPadding(dp(4),0,dp(4),0);setTextColor(Color.rgb(129,213,170));setBackgroundColor(Color.TRANSPARENT);setOnClickListener { action() } };actions.addView(b,LinearLayout.LayoutParams(0,dp(48),1f));return b }
        button(t("Scan","স্ক্যান")) { if(!busy&&!paused&&used<budget){requested=true;nextScan=0} };pauseButton=button(t("Pause","বিরতি")){setPaused(!paused)};button(t("Stop","বন্ধ")){stopSelf()};root.addView(actions)
        layout=WindowManager.LayoutParams(min(dp(240),resources.displayMetrics.widthPixels-dp(24)),WindowManager.LayoutParams.WRAP_CONTENT,if(Build.VERSION.SDK_INT>=26)WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else @Suppress("DEPRECATION")WindowManager.LayoutParams.TYPE_PHONE,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,PixelFormat.TRANSLUCENT).apply { gravity=Gravity.TOP or Gravity.END;x=dp(12);y=dp(80) }
        fun applySize(){detailText?.visibility=if(collapsed)View.GONE else View.VISIBLE;counterText?.visibility=if(collapsed)View.GONE else View.VISIBLE;actions.visibility=if(collapsed)View.GONE else View.VISIBLE;layout!!.width=min(dp(if(collapsed)240 else 300),resources.displayMetrics.widthPixels-dp(24));toggle.text=if(collapsed)"⌄" else "−";toggle.contentDescription=if(collapsed)t("Expand panel","প্যানেল বড় করুন")else t("Minimize panel","প্যানেল ছোট করুন")}
        applySize();toggle.setOnClickListener {collapsed=!collapsed;applySize();window?.updateViewLayout(root,layout)}
        var startX=0;var startY=0;var touchX=0f;var touchY=0f
        heading.setOnTouchListener { _,event -> when(event.action){MotionEvent.ACTION_DOWN->{startX=layout!!.x;startY=layout!!.y;touchX=event.rawX;touchY=event.rawY;true};MotionEvent.ACTION_MOVE->{layout!!.x=(startX-(event.rawX-touchX).toInt()).coerceIn(0,max(0,resources.displayMetrics.widthPixels-layout!!.width));layout!!.y=(startY+(event.rawY-touchY).toInt()).coerceIn(0,max(0,resources.displayMetrics.heightPixels-dp(220)));window?.updateViewLayout(root,layout);true};else->false} }
        window!!.addView(root,layout)
    }
    override fun onTaskRemoved(rootIntent:Intent?) { stopSelf() }
    override fun onDestroy() { active=false;generation++;connection?.disconnect();token="";getSystemService(NotificationManager::class.java).cancel(602);reader?.setOnImageAvailableListener(null,null);display?.release();display=null;reader?.close();reader=null;projection?.stop();projection=null;try {panel?.let { window?.removeView(it) }}catch(_:Exception){};panel=null;capture.removeCallbacksAndMessages(null);frames.clear();previous=null;captureThread.quitSafely();network.shutdownNow();snapshot=mapOf("running" to false,"phase" to "off");stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy() }
}
