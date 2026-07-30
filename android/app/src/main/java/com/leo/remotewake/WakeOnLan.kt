package com.leo.remotewake

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

object WakeOnLan {
    /**
     * 发送 Wake-on-LAN 魔法包。
     * @param mac 目标网卡 MAC 地址，支持 AA:BB:CC:DD:EE:FF / AA-BB-... / AABBCCDDEEFF
     * @param broadcast 广播地址，本地直连一般用 255.255.255.255
     * @param port 目标端口，通常 7 或 9
     */
    fun send(mac: String, broadcast: String = "255.255.255.255", port: Int = 9) {
        val macBytes = parseMac(mac)
        val packet = ByteArray(6 + 16 * 6)
        for (i in 0..5) packet[i] = 0xFF.toByte()
        for (i in 0 until 16) {
            System.arraycopy(macBytes, 0, packet, 6 + i * 6, 6)
        }

        val address = InetAddress.getByName(broadcast)
        DatagramSocket().use { socket ->
            socket.broadcast = true
            socket.send(DatagramPacket(packet, packet.size, address, port))
        }
    }

    private fun parseMac(mac: String): ByteArray {
        val hex = mac.replace(Regex("[^0-9A-Fa-f]"), "")
        require(hex.length == 12) { "MAC 地址格式不正确: $mac" }
        return hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    }
}
