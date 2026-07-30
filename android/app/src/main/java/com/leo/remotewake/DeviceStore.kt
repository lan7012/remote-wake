package com.leo.remotewake

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

object DeviceStore {
    private const val PREFS = "remotewake_devices"
    private const val KEY = "devices"

    private fun prefs(ctx: Context): SharedPreferences =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(ctx: Context): MutableList<Device> {
        val raw = prefs(ctx).getString(KEY, "[]") ?: "[]"
        val list = mutableListOf<Device>()
        try {
            val arr = JSONArray(raw)
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                list.add(
                    Device(
                        id = o.optString("id", ""),
                        name = o.optString("name", ""),
                        mac = o.optString("mac", ""),
                        broadcast = o.optString("broadcast", "255.255.255.255"),
                        port = o.optInt("port", 9),
                        relayUrl = o.optString("relayUrl", ""),
                        token = o.optString("token", "")
                    )
                )
            }
        } catch (e: Exception) {
            // 数据损坏时忽略，返回空列表
        }
        return list
    }

    fun save(ctx: Context, devices: List<Device>) {
        val arr = JSONArray()
        for (d in devices) {
            val o = JSONObject()
            o.put("id", d.id)
            o.put("name", d.name)
            o.put("mac", d.mac)
            o.put("broadcast", d.broadcast)
            o.put("port", d.port)
            o.put("relayUrl", d.relayUrl)
            o.put("token", d.token)
            arr.put(o)
        }
        prefs(ctx).edit().putString(KEY, arr.toString()).apply()
    }
}
