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

/** Explicitly gated emulator test. Normal OS consent screens, never shell grants. */
@RunWith(AndroidJUnit4::class)
class LiveCaptureTest {
    @Test fun capturesOwnedTestVideoAndOnlyWarnsForActualFake() {
        val args=InstrumentationRegistry.getArguments()
        assumeTrue("Per-action consent-test approval required",args.getString("captureConsentApproved")=="true")
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        val device=UiDevice.getInstance(instrumentation)
        fun post(path:String,body:JSONObject?,token:String?=null):JSONObject {
            val c=URL("http://10.0.2.2:8001/api$path").openConnection() as HttpURLConnection
            c.requestMethod="POST";c.connectTimeout=15000;c.readTimeout=15000;c.doOutput=true
            c.setRequestProperty("Content-Type","application/json")
            if(token!=null)c.setRequestProperty("Authorization","Bearer $token")
            c.outputStream.use {it.write((body?:JSONObject()).toString().toByteArray())}
            assertEquals(200,c.responseCode)
            return c.inputStream.bufferedReader().use {JSONObject(it.readText())}.also {c.disconnect()}
        }
        val password=args.getString("testPassword") ?: ""
        assertTrue("Use ignored local test configuration",password.isNotBlank())
        val token=post("/auth/mobile/login",JSONObject().put("username","ui-signup").put("password",password)).getString("token")
        try {
            device.wakeUp()
            context.startActivity(Intent(context,CaptureHarnessActivity::class.java).putExtra("token",token).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            // A human-approved test follows the same OS settings and prompts as a user.
            repeat(2){
                if(device.wait(Until.hasObject(By.checkable(true)),10000)){
                    val toggle=device.findObject(By.checkable(true))
                    if(toggle!=null&&!toggle.isChecked)toggle.click()
                    device.pressBack()
                } else {
                    device.findObject(By.text("DeepShield"))?.click()
                    if(device.wait(Until.hasObject(By.checkable(true)),5000)){
                        val toggle=device.findObject(By.checkable(true));if(toggle!=null&&!toggle.isChecked)toggle.click();device.pressBack()
                    }
                }
            }
            if(device.wait(Until.hasObject(By.text("Allow")),5000))device.findObject(By.text("Allow"))?.click()
            device.wait(Until.hasObject(By.res("android","button1")),15000)
            device.findObject(By.textContains("A single app"))?.click()
            if(device.wait(Until.hasObject(By.textContains("Entire screen")),2000))device.findObject(By.textContains("Entire screen"))?.click()
            val start=device.findObject(By.res("android","button1"))
            assertNotNull("Android screen-sharing confirmation must be visible",start);start!!.click()
            val deadline=System.currentTimeMillis()+180000
            while(System.currentTimeMillis()<deadline&&LiveGuardService.snapshot["resultId"]==null)Thread.sleep(500)
            assertNotNull("Actual capture must produce a saved model result: ${LiveGuardService.snapshot}",LiveGuardService.snapshot["resultId"])
            val warning=LiveGuardService.snapshot["verdict"]=="Fake"
            assertEquals("Only actual Fake may alert",warning,context.getSystemService(NotificationManager::class.java).activeNotifications.any {it.id==602})
            device.takeScreenshot(File(context.getExternalFilesDir(null),"overlay-capture-test.png"))
            assertTrue("Observe the actual model result on the supplied Fake video",warning)
            context.stopService(Intent(context,LiveGuardService::class.java))
            val stopDeadline=System.currentTimeMillis()+5000
            while(System.currentTimeMillis()<stopDeadline&&LiveGuardService.snapshot["running"]==true)Thread.sleep(100)
            assertEquals(false,LiveGuardService.snapshot["running"])
            assertFalse(context.getSystemService(NotificationManager::class.java).activeNotifications.any {it.id==601||it.id==602})
        } finally {
            context.stopService(Intent(context,LiveGuardService::class.java))
            post("/auth/mobile/logout",null,token)
        }
    }
}
