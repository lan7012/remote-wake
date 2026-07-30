package com.leo.remotewake

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.leo.remotewake.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var adapter: DeviceAdapter
    private val devices = mutableListOf<Device>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = DeviceAdapter(
            onWake = { wake(it) },
            onDelete = { delete(it) },
            onEdit = { edit(it) }
        )
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter

        binding.fabAdd.setOnClickListener {
            startActivity(Intent(this, AddEditDeviceActivity::class.java))
        }
    }

    override fun onResume() {
        super.onResume()
        devices.clear()
        devices.addAll(DeviceStore.load(this))
        adapter.submit(devices)
        binding.emptyTip.visibility = if (devices.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun delete(device: Device) {
        devices.removeIf { it.id == device.id }
        DeviceStore.save(this, devices)
        adapter.submit(devices)
        binding.emptyTip.visibility = if (devices.isEmpty()) View.VISIBLE else View.GONE
        Toast.makeText(this, "已删除 ${device.name}", Toast.LENGTH_SHORT).show()
    }

    private fun edit(device: Device) {
        val intent = Intent(this, AddEditDeviceActivity::class.java)
        intent.putExtra("device_id", device.id)
        startActivity(intent)
    }

    private fun wake(device: Device) {
        runOnUiThread { adapter.updateResult(device.id, "正在发送...") }
        Thread {
            try {
                val msg = if (device.usesRelay) {
                    RelayClient.wake(device.relayUrl, device.mac, device.token)
                } else {
                    WakeOnLan.send(device.mac, device.broadcast, device.port)
                    "已发送唤醒包 (本机直连)"
                }
                runOnUiThread {
                    adapter.updateResult(device.id, msg)
                    Toast.makeText(this, "${device.name} 已执行", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                val detail = "${e.javaClass.simpleName}: ${e.message}"
                runOnUiThread {
                    adapter.updateResult(device.id, "失败\n$detail")
                    Toast.makeText(this, "${device.name} 失败", Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }
}
