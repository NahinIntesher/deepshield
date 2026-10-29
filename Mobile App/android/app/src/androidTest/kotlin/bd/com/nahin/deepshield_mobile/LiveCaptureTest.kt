package bd.com.nahin.deepshield_mobile

import android.app.NotificationManager
import android.content.Intent
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/** Gated, local-only model test using normal Android consent screens. */
@RunWith(AndroidJUnit4::class)
class LiveCaptureTest {
    @Test fun fakeCaptureWarnsAndClearsOutsideAllowedApp() = capture("sample_fake.mp4", "Fake")
    @Test fun realCaptureDoesNotNotify() = capture("sample_real.mp4", "Real")

    private fun capture(sample:String, expected:String) {
        val args=InstrumentationRegistry.getArguments()
        assumeTrue("Explicit consent-test approval required",args.getString("captureConsentApproved")=="true")
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        val device=UiDevice.getInstance(instrumentation)
        fun post(path:String,body:JSONObject?,token:String?=null):JSONObject {
            val c=URL("http://10.0.2.2:8001/api$path").openConnection() as HttpURLConnection
            c.requestMethod="POST";c.connectTimeout=15000;c.readTimeout=15000;c.doOutput=true
            c.setRequestProperty("Content-Type","application/json")
            if(token!=null)c.setRequestProperty("Authorization","Bearer $token")
            try {
                c.outputStream.use {it.write((body?:JSONObject()).toString().toByteArray())}
                assertEquals("Local test API must accept this request",200,c.responseCode)
                return c.inputStream.bufferedReader().use {JSONObject(it.readText())}
            } finally {c.disconnect()}
        }
        fun waitFor(timeout:Long=15000, condition:()->Boolean):Boolean {
            val end=System.currentTimeMillis()+timeout
            while(System.currentTimeMillis()<end){if(condition())return true;Thread.sleep(100)}
            return condition()
        }
        fun approveCurrentAppSetting() {
            device.waitForIdle()
            if(!device.wait(Until.hasObject(By.checkable(true)),3000)) {
                val row=device.wait(Until.findObject(By.text("DeepShield")),10000)
                assertNotNull("The system settings must name DeepShield",row);row!!.click()
            }
            val toggle=device.wait(Until.findObject(By.checkable(true)),10000)
            assertNotNull("Expected the normal Android permission switch",toggle)
            if(!toggle!!.isChecked)toggle.click()
            device.pressBack();device.waitForIdle()
            if(device.currentPackageName=="com.android.settings"){device.pressBack();device.waitForIdle()}
        }
        val password=args.getString("testPassword") ?: ""
        assertTrue("Use ignored local test configuration",password.isNotBlank())
        val token=post("/auth/mobile/login",JSONObject().put("username","ui-signup").put("password",password)).getString("token")
        val overlayNeeded=!android.provider.Settings.canDrawOverlays(context)
        val usageNeeded=!AppAccess.allowed(context)
        val notificationsNeeded=android.os.Build.VERSION.SDK_INT>=33 && context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED
        try {
            device.wakeUp()
            context.startActivity(Intent(context,CaptureHarnessActivity::class.java).putExtra("token",token).putExtra("samplePath",sample).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            if(overlayNeeded)approveCurrentAppSetting()
            if(usageNeeded)approveCurrentAppSetting()
            if(notificationsNeeded){
                val allow=device.wait(Until.findObject(By.text("Allow")),10000)
                assertNotNull("Expected Android notification consent",allow);allow!!.click()
            }
            assertTrue("The normal screen-sharing prompt must appear",device.wait(Until.hasObject(By.res("android","button1")),15000))
            device.findObject(By.textContains("A single app"))?.click()
            device.wait(Until.findObject(By.textContains("Entire screen")),2000)?.click()
            val start=device.findObject(By.res("android","button1"))
            assertNotNull("Screen-sharing confirmation must remain visible",start);start!!.click()
            var exportedAt=0L
            val complete=waitFor(180000){
                if(System.currentTimeMillis()-exportedAt>3000){
                    exportedAt=System.currentTimeMillis()
                    File(context.getExternalFilesDir(null),"capture-current.json").writeText(JSONObject(LiveGuardService.snapshot).toString(2))
                    device.takeScreenshot(File(context.getExternalFilesDir(null),"capture-current.png"))
                }
                LiveGuardService.snapshot["resultId"]!=null
            }
            assertTrue("Actual capture did not reach the model: ${LiveGuardService.snapshot}",complete)
            val savedId=LiveGuardService.snapshot["resultId"]
            val read=URL("http://10.0.2.2:8001/api/profile/detections/$savedId").openConnection() as HttpURLConnection
            read.connectTimeout=15000;read.readTimeout=15000
            read.setRequestProperty("Authorization","Bearer $token")
            val saved=try {assertEquals(200,read.responseCode);read.inputStream.bufferedReader().use {JSONObject(it.readText())}} finally {read.disconnect()}
            val actual=saved.getString("verdict")
            val evidence=JSONObject(LiveGuardService.snapshot).put("fixture",sample).put("expected",expected).put("actualModelVerdict",actual).put("modelScorePercent",saved.optDouble("confidence_percentage"))
            val notifications=context.getSystemService(NotificationManager::class.java)
            if(actual=="Fake")assertTrue("Fake must raise the warning notification",waitFor(5000){notifications.activeNotifications.any {it.id==602}})
            else assertFalse("Real must not raise a warning notification",notifications.activeNotifications.any {it.id==602})
            evidence.put("warningNotification",notifications.activeNotifications.any {it.id==602})
            File(context.getExternalFilesDir(null),"capture-$expected.json").writeText(evidence.toString(2))
            device.takeScreenshot(File(context.getExternalFilesDir(null),"capture-$expected.png"))
            assertEquals("Record actual model output; do not fabricate the expected result",expected,actual)
            device.pressHome()
            assertTrue("Leaving allowed apps must clear the warning",waitFor(10000){LiveGuardService.snapshot["phase"]=="outside"})
            assertFalse("No stale warning may remain outside the selected app",notifications.activeNotifications.any {it.id==602})
        } finally {
            context.stopService(Intent(context,LiveGuardService::class.java))
            assertTrue("Stop must release screen sharing",waitFor(5000){LiveGuardService.snapshot["running"]==false})
            post("/auth/mobile/logout",null,token)
        }
    }
}
