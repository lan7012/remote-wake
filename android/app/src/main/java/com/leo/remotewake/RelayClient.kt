package com.leo.remotewake

import java.net.HttpURLConnection
import java.net.URL

object RelayClient {
    /**
     * 通过家里的中继服务器远程唤醒。
     * 中继地址示例：http://你的域名:8080/wake
     * @return 给人看的结果描述
     */
    fun wake(relayUrl: String, mac: String, token: String): String {
        try {
            val url = URL(relayUrl)
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.connectTimeout = 10000
            conn.readTimeout = 10000
            conn.setRequestProperty("Content-Type", "application/json")

            val escapedMac = mac.replace("\"", "\\\"")
            val escapedToken = token.replace("\"", "\\\"")
            val body = """{"mac":"$escapedMac","token":"$escapedToken"}"""

            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }

            val code = conn.responseCode
            val resp = try {
                conn.inputStream.bufferedReader().use { it.readText() }
            } catch (e: Exception) {
                try {
                    conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                } catch (e2: Exception) {
                    ""
                }
            }
            return if (code in 200..299) {
                "中继已发送唤醒包 (HTTP $code)"
            } else {
                "中继返回错误 (HTTP $code): $resp"
            }
        } catch (e: Exception) {
            val msg = e.message ?: e.javaClass.simpleName
            if (msg.contains("TLS", ignoreCase = true) || msg.contains("SSL", ignoreCase = true)) {
                throw Exception("中继地址协议错误：请使用 http:// 而不是 https:// ($msg)", e)
            }
            throw e
        }
    }
}
