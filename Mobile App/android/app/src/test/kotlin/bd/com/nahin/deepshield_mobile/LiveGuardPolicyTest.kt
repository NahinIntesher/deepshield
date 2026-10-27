package bd.com.nahin.deepshield_mobile

import org.junit.Assert.*
import org.junit.Test

class LiveGuardPolicyTest {
    @Test fun realResultsNeverAlert() {
        assertFalse(LiveGuardPolicy.shouldAlert("Real", 2, 2, false, -1))
    }
    @Test fun onlyCurrentUnpausedFakeAlertsOnce() {
        assertTrue(LiveGuardPolicy.shouldAlert("Fake", 2, 2, false, -1))
        assertFalse(LiveGuardPolicy.shouldAlert("Fake", 2, 3, false, -1))
        assertFalse(LiveGuardPolicy.shouldAlert("Fake", 2, 2, true, -1))
        assertFalse(LiveGuardPolicy.shouldAlert("Fake", 2, 2, false, 2))
        assertFalse(LiveGuardPolicy.shouldAlert("Unknown", 2, 2, false, -1))
    }
    @Test fun captureOnlyUsesSelectedApps() {
        val selected=setOf("YouTube", "Facebook", "Instagram")
        assertEquals("YouTube", LiveGuardPolicy.sourceFor("com.google.android.youtube", selected, null))
        assertEquals("Facebook", LiveGuardPolicy.sourceFor("com.facebook.lite", selected, null))
        assertEquals("Instagram", LiveGuardPolicy.sourceFor("com.instagram.android", selected, null))
        assertNull(LiveGuardPolicy.sourceFor("com.android.settings", selected, null))
        assertNull(LiveGuardPolicy.sourceFor("com.google.android.youtube", emptySet(), null))
        assertNull(LiveGuardPolicy.sourceFor(null, selected, null))
        assertEquals("Other", LiveGuardPolicy.sourceFor("example.selected.player", setOf("Other"), "example.selected.player"))
        assertNull(LiveGuardPolicy.sourceFor("example.unselected.player", setOf("Other"), "example.selected.player"))
    }
}
