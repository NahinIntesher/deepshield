package bd.com.nahin.deepshield_mobile

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.widget.FrameLayout
import android.widget.VideoView

/** Local emulator harness only. These activities are absent from release APKs. */
class CaptureHarnessActivity : Activity() {
    override fun onCreate(state: Bundle?) {super.onCreate(state); requestNext()}
    private fun requestNext() {
        when {
            !Settings.canDrawOverlays(this) -> startActivityForResult(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:$packageName")),901)
            !AppAccess.allowed(this) -> startActivityForResult(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS,Uri.parse("package:$packageName")),902)
            Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED -> requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),903)
            else -> startActivityForResult(getSystemService(MediaProjectionManager::class.java).createScreenCaptureIntent(),991)
        }
    }
    override fun onRequestPermissionsResult(code:Int,permissions:Array<out String>,grants:IntArray) {
        super.onRequestPermissionsResult(code,permissions,grants)
        if(code==903){if(grants.firstOrNull()==PackageManager.PERMISSION_GRANTED)requestNext() else finish()}
    }
    override fun onActivityResult(request:Int,result:Int,data:Intent?) {
        super.onActivityResult(request,result,data)
        if(request==901){if(Settings.canDrawOverlays(this))requestNext() else finish();return}
        if(request==902){if(AppAccess.allowed(this))requestNext() else finish();return}
        if(request==991 && result==RESULT_OK && data!=null){
            val service=Intent(this,LiveGuardService::class.java)
                .putExtra("permission",data).putExtra("resultCode",result)
                .putExtra("apiBase","http://10.0.2.2:8001").putExtra("token",intent.getStringExtra("token"))
                .putExtra("language","en").putExtra("source","Other")
                .putStringArrayListExtra("allowedSources",arrayListOf("Other"))
                .putExtra("otherPackage",packageName).putExtra("budget",1).putExtra("automatic",true)
            if(Build.VERSION.SDK_INT>=26)startForegroundService(service) else startService(service)
            startActivity(Intent(this,SamplePlayerActivity::class.java))
        }
        finish()
    }
}

class SamplePlayerActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val root=FrameLayout(this);val video=VideoView(this)
        root.addView(video,FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));setContentView(root)
        video.setVideoURI(Uri.parse("http://10.0.2.2:8787/sample.mp4"))
        video.setOnPreparedListener {it.isLooping=true;video.start()}
    }
}
