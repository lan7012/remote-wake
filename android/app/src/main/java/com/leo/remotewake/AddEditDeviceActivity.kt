package com.leo.remotewake

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.leo.remotewake.databinding.ActivityAddEditBinding
import java.util.UUID

class AddEditDeviceActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAddEditBinding
    private var editingId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAddEditBinding.inflate(layoutInflater)
        setContentView(binding.root)

        editingId = intent.getStringExtra("device_id")
        val existing = editingId?.let { id ->
            DeviceStore.load(this).firstOrNull { it.id == id }
        }

        if (existing != null) {
            title = getString(R.string.edit_device)
            binding.etName.setText(existing.name)
            binding.etMac.setText(existing.mac)
            binding.etBroadcast.setText(existing.broadcast)
            binding.etPort.setText(existing.port.toString())
            binding.etRelay.setText(existing.relayUrl)
            binding.etToken.setText(existing.token)
        } else {
            title = getString(R.string.add_device)
        }

        binding.btnSave.setOnClickListener { save(existing) }
    }

    private fun save(existing: Device?) {
        val name = binding.etName.text.toString().trim()
        val mac = binding.etMac.text.toString().trim()
        val broadcast = binding.etBroadcast.text.toString().trim().ifBlank { "255.255.255.255" }
        val portStr = binding.etPort.text.toString().trim()
        val relay = binding.etRelay.text.toString().trim().let { url ->
            if (url.isBlank()) return@let url
            var fixed = url
            if (!fixed.startsWith("http://", ignoreCase = true) && !fixed.startsWith("https://", ignoreCase = true)) {
                fixed = "http://$fixed"
            }
            fixed = fixed.trimEnd('/')
            if (!fixed.endsWith("/wake", ignoreCase = true)) {
                fixed = "$fixed/wake"
            }
            fixed
        }
        val token = binding.etToken.text.toString().trim()

        if (mac.isBlank()) {
            Toast.makeText(this, "请填写 MAC 地址", Toast.LENGTH_SHORT).show()
            return
        }
        val port = portStr.toIntOrNull() ?: 9

        val device = Device(
            id = existing?.id ?: UUID.randomUUID().toString(),
            name = name,
            mac = mac,
            broadcast = broadcast,
            port = port,
            relayUrl = relay,
            token = token
        )

        val list = DeviceStore.load(this).toMutableList()
        if (existing != null) {
            val idx = list.indexOfFirst { it.id == existing.id }
            if (idx >= 0) list[idx] = device else list.add(device)
        } else {
            list.add(device)
        }
        DeviceStore.save(this, list)
        Toast.makeText(this, "已保存", Toast.LENGTH_SHORT).show()
        finish()
    }
}
