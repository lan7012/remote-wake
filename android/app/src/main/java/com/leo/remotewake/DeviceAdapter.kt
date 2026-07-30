package com.leo.remotewake

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.leo.remotewake.databinding.ItemDeviceBinding

class DeviceAdapter(
    private val onWake: (Device) -> Unit,
    private val onDelete: (Device) -> Unit,
    private val onEdit: (Device) -> Unit
) : RecyclerView.Adapter<DeviceAdapter.VH>() {

    private val items = mutableListOf<Device>()
    private val results = mutableMapOf<String, String>()

    fun submit(list: List<Device>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    fun updateResult(deviceId: String, result: String) {
        results[deviceId] = result
        notifyDataSetChanged()
    }

    class VH(val binding: ItemDeviceBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemDeviceBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val d = items[position]
        holder.binding.tvName.text = d.name.ifBlank { "未命名设备" }
        holder.binding.tvMac.text = "MAC: ${d.mac}"
        holder.binding.tvMode.text = if (d.usesRelay) "模式: 远程中继" else "模式: 本机直连"

        val result = results[d.id]
        if (result.isNullOrBlank()) {
            holder.binding.tvResult.visibility = View.GONE
            holder.binding.tvResult.text = ""
        } else {
            holder.binding.tvResult.visibility = View.VISIBLE
            holder.binding.tvResult.text = result
        }

        holder.binding.btnWake.setOnClickListener { onWake(d) }
        holder.binding.btnDelete.setOnClickListener { onDelete(d) }
        holder.binding.root.setOnClickListener { onEdit(d) }
    }

    override fun getItemCount(): Int = items.size
}
