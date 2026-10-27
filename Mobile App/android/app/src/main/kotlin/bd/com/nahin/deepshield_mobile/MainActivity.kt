package bd.com.nahin.deepshield_mobile

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var pending: MethodChannel.Result? = null
    private var configuration: Map<*, *>? = null
    private var pickedPackage: String? = null
    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        MethodChannel(engine.dartExecutor.binaryMessenger, "deepshield/live_guard").setMethodCallHandler { call, result ->
            when (call.method) {
                "status" -> result.success(LiveGuardService.snapshot + mapOf("overlayAllowed" to Settings.canDrawOverlays(this), "usageAllowed" to AppAccess.allowed(this), "notificationsAllowed" to (Build.VERSION.SDK_INT < 33 || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED)))
                "usagePermission" -> {
                    if (pending != null) result.error("BUSY", "A permission request is already open.", null)
                    else { pending = result; startActivityForResult(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS, Uri.parse("package:$packageName")), 705) }
                }
                "chooseApp" -> {
                    if (pending != null) result.error("BUSY", "A permission request is already open.", null)
                    else { pending = result; startActivityForResult(Intent(Intent.ACTION_PICK_ACTIVITY).putExtra(Intent.EXTRA_INTENT, Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)).putExtra(Intent.EXTRA_TITLE, "Choose an app for Live Guard"), 704) }
                }
                "stop" -> { stopService(Intent(this, LiveGuardService::class.java)); result.success(true) }
                "pause", "resume", "scan" -> { startService(Intent(this, LiveGuardService::class.java).setAction(call.method)); result.success(true) }
                "overlayPermission" -> {
                    if (pending != null) result.error("BUSY", "A permission request is already open.", null)
                    else if (Settings.canDrawOverlays(this)) result.success(true)
                    else { pending = result; startActivityForResult(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")), 701) }
                }
                "notificationPermission" -> {
                    if (Build.VERSION.SDK_INT < 33 || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) result.success(true)
                    else if (pending != null) result.error("BUSY", "A permission request is already open.", null)
                    else { pending = result; requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 702) }
                }
                "start" -> {
                    val args = call.arguments as? Map<*, *>
                    val address = args?.get("apiBase") as? String ?: ""
                    val uri = Uri.parse(address)
                    val allowed = (uri.scheme == "https" && uri.host == "api.deepshield.nahin.com.bd") || (BuildConfig.DEBUG && uri.scheme == "http" && uri.host in listOf("10.0.2.2", "localhost", "127.0.0.1"))
                    if (!allowed || !(args?.get("token") as? String ?: "").startsWith("dsm_")) result.error("SESSION", "Sign in again before starting Live Guard.", null)
                    else if (!Settings.canDrawOverlays(this)) result.error("PERMISSION", "Allow the floating panel first.", null)
                    else if (!AppAccess.allowed(this)) result.error("PERMISSION", "Allow app access so scans pause outside your chosen apps.", null)
                    else if ((args?.get("allowedSources") as? List<*>)?.filterIsInstance<String>()?.any { it in LiveGuardPolicy.packages.keys || it == "Other" && pickedPackage != null && pickedPackage == args?.get("otherPackage") } != true) result.error("PERMISSION", "Choose at least one app for scanning.", null)
                    else if (pending != null || LiveGuardService.snapshot["running"] == true) result.error("BUSY", "Stop the current session before starting another.", null)
                    else { pending = result; configuration = args; startActivityForResult(getSystemService(MediaProjectionManager::class.java).createScreenCaptureIntent(), 703) }
                }
                else -> result.notImplemented()
            }
        }
    }
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 701) { pending?.success(Settings.canDrawOverlays(this)); pending = null }
        if (requestCode == 705) { pending?.success(AppAccess.allowed(this)); pending = null }
        if (requestCode == 704) {
            pickedPackage = if (resultCode == Activity.RESULT_OK) data?.component?.packageName?.takeIf { it != packageName } else null
            val selected = pickedPackage?.let { p -> mapOf("package" to p, "name" to packageManager.getApplicationLabel(packageManager.getApplicationInfo(p, 0)).toString()) }
            pending?.success(selected); pending = null
        }
        if (requestCode == 703) {
            val callback = pending; pending = null
            if (resultCode != Activity.RESULT_OK || data == null) callback?.success(false)
            else {
                val args = configuration ?: emptyMap<Any, Any>(); configuration = null
                val intent = Intent(this, LiveGuardService::class.java).putExtra("permission", data).putExtra("resultCode", resultCode)
                    .putExtra("apiBase", args["apiBase"] as? String).putExtra("token", args["token"] as? String)
                    .putExtra("source", args["source"] as? String ?: "Other").putExtra("language", args["language"] as? String ?: "en")
                    .putExtra("interval", (args["interval"] as? Number)?.toInt() ?: 120).putExtra("budget", (args["budget"] as? Number)?.toInt() ?: 3)
                    .putExtra("automatic", args["automatic"] as? Boolean ?: true)
                    .putStringArrayListExtra("allowedSources", ArrayList((args["allowedSources"] as? List<*>)?.filterIsInstance<String>()?.filter { it in LiveGuardPolicy.packages.keys || it == "Other" && pickedPackage != null && pickedPackage == args["otherPackage"] } ?: emptyList()))
                    .putExtra("otherPackage", pickedPackage)
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
                callback?.success(true)
            }
            configuration = null
        }
    }
    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, grants: IntArray) {
        super.onRequestPermissionsResult(code, permissions, grants)
        if (code == 702) { pending?.success(grants.firstOrNull() == PackageManager.PERMISSION_GRANTED); pending = null }
    }
}
