package bd.com.nahin.deepshield_mobile

/** Pure decisions, shared by permission setup and the running capture session. */
object LiveGuardPolicy {
    val packages = mapOf(
        "YouTube" to setOf("com.google.android.youtube"),
        "Facebook" to setOf("com.facebook.katana", "com.facebook.lite"),
        "Instagram" to setOf("com.instagram.android"),
        "TikTok" to setOf("com.zhiliaoapp.musically", "com.ss.android.ugc.trill")
    )
    fun sourceFor(packageName: String?, allowed: Set<String>, otherPackage: String?): String? {
        if (packageName == null) return null
        return packages.entries.firstOrNull { it.key in allowed && packageName in it.value }?.key
            ?: if ("Other" in allowed && packageName == otherPackage) "Other" else null
    }
    fun shouldAlert(verdict: String, captured: Int, current: Int, paused: Boolean, lastAlert: Int): Boolean =
        verdict == "Fake" && captured == current && !paused && lastAlert != captured
}
