package bd.com.nahin.deepshield_mobile

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.Process

object AppAccess {
    fun allowed(context: Context): Boolean = context.getSystemService(AppOpsManager::class.java)
        .checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName) == AppOpsManager.MODE_ALLOWED

    /** Only the current foreground package is kept; no app-usage history is stored or sent. */
    fun foreground(context: Context, previous: String?): String? {
        if (!allowed(context)) return null
        val now = System.currentTimeMillis()
        val events = context.getSystemService(UsageStatsManager::class.java).queryEvents(now - 60_000, now)
        val event = UsageEvents.Event()
        var current = previous
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            if (event.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND) current = event.packageName
        }
        return current
    }
}
