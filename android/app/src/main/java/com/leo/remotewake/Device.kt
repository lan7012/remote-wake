package com.leo.remotewake

import java.util.UUID

data class Device(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val mac: String,
    val broadcast: String = "255.255.255.255",
    val port: Int = 9,
    val relayUrl: String = "",
    val token: String = ""
) {
    val usesRelay: Boolean get() = relayUrl.isNotBlank()
}
