# 远程开机 · 你的设备专属配置指南

你的实际设备组合：

| 角色 | 设备 | 系统 |
|---|---|---|
| **被唤醒的目标** | 华硕主板的台式机/电脑 | Windows（默认） |
| **中继（常年开机）** | 安卓平板 | Android（Termux 跑中继） |
| **远程控制** | 安卓手机 | Android（装 RemoteWake App） |

```
安卓手机(外地/任意网络)
      │  HTTPS / HTTP
      ▼
安卓平板(家里 Wi-Fi 常开，跑中继 relay_server.py)
      │  UDP 魔法包（局域网广播）
      ▼
华硕电脑(同一路由器/同一局域网，被唤醒)
```

> 关键点：WoL 魔法包是 UDP 广播，路由器**不会**把它转到外网。
> 所以必须由**和你电脑在同一局域网的安卓平板**来发这个包。手机只负责通知平板「去唤醒」。

---

## 设备①：华硕电脑（目标，被唤醒）

### 1) BIOS / UEFI 开启 Wake-on-LAN
1. 开机时连续按 **`Del`**（部分华硕主板用 `F2`）进 BIOS。
2. 按 **`F7`** 进入「Advance Mode（高级模式）」。
3. 进入 **Advanced（高级）→ APM Configuration（高级电源管理）**：
   - 把 **`Power On By PCI-E`**（或 `Wake on PCI-E` / `Power On By PCI`）设为 **`Enabled`**。
     > 华硕主板没有单独叫 "Wake on LAN" 的选项，通常就是这一项（PCI-E 网卡走的就是它）。
   - 找到 **`ErP Ready`**（或 `ErP S4+S5`），**必须设为 `Disabled`**。
     > ⚠️ ErP 节能会在关机后切断网卡供电，WoL 会彻底失效。这是华硕最容易踩的坑。
4. 按 **`F10`** 保存并退出。

> 不同华硕型号选项名略有差异（如老主板在 `Power` 菜单、新主板在 `Advanced\Onboard Devices`）。
> 总原则：开启「PCI-E/PCI 唤醒」，**关闭 ErP/深度节能**。

### 2) Windows 网卡开启唤醒（以 Intel/Realtek 板载网卡为例）
1. `Win + X` → 设备管理器 → **网络适配器** → 你的网卡（以太网，或 Wi‑Fi）→ 右键「属性」。
2. **电源管理** 选项卡：
   - ☑ **允许此设备唤醒计算机**
   - ☑ **只允许幻数据包唤醒计算机**（最安全，避免鼠标/键盘误唤醒）
3. **高级** 选项卡，把以下项设为**启用/Enabled**：
   - `Wake on Magic Packet`（幻数据包唤醒）
   - `Wake on LAN` / `WOL`
   - `关机网络唤醒` / `Shutdown Wake On Lan`
   - 建议把 `Green Ethernet`、`Energy Efficient Ethernet`、`节能以太网` 设为 **Disabled**（省电模式有时会让关机后网卡不收包）。
4. 确定保存。

> **找不到「网卡设置」/「电源管理」选项卡？常见情况：**
> - **找不到网络适配器**：`Win+X` → 设备管理器 → 展开「网络适配器」，里面就是网卡（名字带 `Intel`/`Realtek`/`Killer`/`以太网`/`Wi‑Fi` 的都是）。右键它 → 属性。
> - **属性里没有「电源管理」选项卡**：部分网卡驱动不显示该选项卡。这时**只要 BIOS 那一步（开 PCI-E 唤醒 + 关 ErP）做对了，Windows 这步可以跳过**——绝大多数华硕主板 BIOS 开 WoL 后就能唤醒。也可在「高级」选项卡里找 `Wake on Magic Packet` 设为启用（见下）。
> - **用的是 Wi‑Fi 无线网卡**：同样在「高级」里找 `Wake on Magic Packet` / `WOL` 启用；部分 Wi‑Fi 网卡不支持关机唤醒，建议电脑用**有线**（网线插主板网卡）最稳。
> - **「高级」里找不到 WoL 相关项**：说明驱动较旧，去华硕官网下载对应主板的最新网卡驱动装上，选项卡就出来了。

### 3) 记下 MAC 地址
```
Win + R → 输入 cmd →  ipconfig /all
```
找到你正在用的网卡，「**物理地址**」就是 MAC，形如 `AA-BB-CC-DD-EE-FF`。记下来，后面平板和手机都要用。

> 测试建议：先在「同 Wi‑Fi 下用手机直连唤醒」验证电脑本身没问题（见设备③第 2 步「留空中继」），再上平板中继。

---

## 设备②：安卓平板（中继，常年开机）

平板跑不了原生 Python 服务，但装 **Termux**（安卓上的 Linux 终端）就能直接跑我写好的 `relay_server.py`。

> 📌 **平板（中继）不需要任何「网卡唤醒 / WoL」设置！** 那是**华硕电脑**才要做的。
> 平板只要连上家里 Wi‑Fi、Termux 在后台活着即可当中继。

### 1) 安装 Termux
- 从 **F-Droid** 搜 `Termux` 安装（Google Play 上的版本已停止更新，推荐 F-Droid）。
- 首次打开，等待它初始化完成。

### 2) 在平板里准备中继程序
把 `relay/` 整个目录传到平板（微信文件传输/数据线/U 盘都行），记下它在 Termux 里的路径。
例如放到 `Download/relay`，在 Termux 里：
```sh
cd /storage/shared/Download/relay
pkg update && pkg install -y python
```

### 3) 配置 token 和 MAC
推荐做法：保留默认的 `config.json` 作为模板，**把你的 token 和 MAC 单独写在 `config.user.json` 里**。这样以后更新 relay zip 包时，你的私有配置不会被覆盖。

在 Termux 里创建 `relay/config.user.json`：
```json
{
  "token": "REPLACE_WITH_YOUR_OWN_TOKEN",
  "devices": {
    "pc1": "D4:5D:64:AD:0C:6D"
  }
}
```
- `token`：手机端填同一个值。上面这串是项目已生成好的，可直接用；想换也可以自己改。
- `devices.pc1`：填你的华硕电脑 MAC（用 `:` 分隔，例如 `D4:5D:64:AD:0C:6D`），这样手机唤醒时只传 `device:"pc1"` 就行。

> 如果你只改 `config.json` 也可以，但重新解压 zip 时会被模板覆盖，容易把 MAC 冲回 `AA:BB:CC:DD:EE:FF`。

### 4) 让它「常年在线」的关键设置 ⚠️
你**不需要**让平板一直保持唤醒（不需要 `termux-wake-lock`，那会强制 CPU 不睡、费电）。
中继是网络监听服务，手机发来请求时 Android 内核会自动唤醒进程处理，所以**息屏、CPU 睡眠都能正常收命令**。
真正要做的只有：让 Termux 不被系统后台杀掉。

1. **关闭 Termux 的电池优化（必须）**：设置 → 应用 → Termux → 电池 → 选**不受限制 / 无限制**。
2. **关闭 Tailscale 的电池优化（必须）**：同上，把 Tailscale 也设为不受限制，否则 VPN 断开后手机就找不到平板。
3. **不要从「最近任务」里划掉 Termux**（划掉=强制关闭，中继就停了）。让它留在后台即可。
4. **一直插着充电器**（推荐，非必须）：平板电量够也能跑，只是长期建议插电。
   - 「开发者选项 → 充电时保持唤醒」**不需要开**，那会让屏幕常亮，反而没必要。
5. **开机自启（可选）**：装 **Termux:Boot**（F-Droid），在 `~/.termux/boot/`（即 `/data/data/com.termux/files/home/.termux/boot/`）放个脚本：
   ```sh
   #!/bin/sh
   cd /storage/shared/Download/relay && python relay_server.py &
   ```
   平板重启后会自动拉起中继（同样不需要 wakelock）。

> 如果某天发现外地连不上，先查：平板是否在线、Termux 是否被杀、Tailscale 是否连着（手机和都进 Tailscale 看设备是否在线）。

### 5) 先一键自测（推荐，确认链路通）
```sh
cd /storage/shared/Download/relay
sh verify_termux.sh
```
脚本会自动启动中继、做健康检查、发一次真实唤醒包并打印结果解读：
- `/status` 返回 `ok` → 中继在监听
- `/wake` 返回 `ok` → 魔法包已发出（此时电脑应被唤醒/或已开机）
把输出发回给助手核对即可。

### 6) 启动中继
```sh
cd /storage/shared/Download/relay
sh start_termux.sh
# 我们的脚本默认不获取 wakelock，息屏也能工作
```
看到 `[启动] 监听 0.0.0.0:8080` 即成功。本机手动自测（等价于 verify 脚本里那步）：
```sh
curl -X POST http://127.0.0.1:8080/wake -d "{\"device\":\"pc1\",\"token\":\"你的token\"}"
```
返回 `{"ok": true, ...}` 说明魔法包已发出。

> 平板和电脑要连**同一个路由器**（同一个 Wi‑Fi 或有线）。如果电脑是有线、平板是 Wi‑Fi，只要在同一台路由器下、同一网段（如都 `192.168.1.x`），广播就能到达。

---

## 设备③：安卓手机（远程控制）

### 1) 安装 App
把已编译好的 **`app-debug.apk`** 传到手机安装（允许「未知来源」安装）。

### 2) 添加设备
打开 App → 右下角 **＋**：
- **设备名称**：随便，如「华硕台式机」
- **MAC 地址**：华硕电脑的物理地址
- **广播地址 / 端口**：手机和电脑**同一 Wi‑Fi 时直接唤醒**才用，默认即可；走平板中继时这里可留空
- **中继地址**：见下方「外网连通」二选一后的地址，例如 `http://100.100.10.20:8080/wake`
- **中继令牌**：与 `config.json` 里的 `token` 一致
- 想让手机在**同一 Wi‑Fi 下直接唤醒电脑**（不经过平板），把「中继地址」留空即可。

保存后点卡片上的「唤醒」按钮。点卡片本身=编辑，右上角垃圾桶=删除。

---

## 让外地手机能连上家里的平板（外网连通，二选一）

### 方案 A：Tailscale（强烈推荐，最省事最安全）✅
1. 平板和手机都装 **Tailscale**（App Store / Google Play / F-Droid），用同一账号登录。
2. 在平板的 Tailscale 里把中继服务跑起来（它监听 `0.0.0.0`，Tailscale 虚拟网卡也能收到）。
3. 手机端「中继地址」填平板的 **Tailscale IP**（形如 `http://100.x.x.x:8080/wake`）。
   - 在 Tailscale App 里点平板设备即可看到它的 IP。
4. 无需路由器改端口、无需公网 IP、自带加密，手机在全世界任何有网的地方都能唤醒。

> 注意：平板上的 Tailscale 也要「关闭电池优化 + 保持联网」，否则断开后手机就找不到它了。

### 方案 B：路由器端口转发 + DDNS（传统方案）
1. 路由器里把 **外部端口**（如 `18080`）→ 平板**局域网 IP**（建议在路由器给平板绑**静态 IP**）→ 内部端口 `8080` → 协议 `TCP`。
2. 路由器开启 DDNS（花生壳/阿里云/腾讯云等）得到域名，如 `myhome.example.com`。
3. 手机「中继地址」填 `http://myhome.example.com:18080/wake`。
4. 安全起见，建议把 `config.json` 的 `use_ssl` 设为 `true` 并配置证书，或改用 Tailscale。

> ⚠️ 无论哪种方案，都不要裸奔公网 HTTP + 弱 token，否则别人也能唤醒你的电脑。强 token +（Tailscale 或 HTTPS）是底线。

---

## 五、常见问题排查

| 现象 | 排查 |
|---|---|
| 同 Wi‑Fi 能唤醒，外地不行 | 平板没连上外网/Tailscale 断开；或端口转发/DDNS 没配好；token 不一致 |
| 平板日志没收到请求 | 手机「中继地址」填错（应是平板 Tailscale IP 或域名:端口/wake）；Tailscale 未连 |
| 平板收到请求但电脑不醒 | 华硕 BIOS 没开 PCI-E 唤醒、ErP 没关；Windows 网卡电源管理没开；电脑**彻底拔电**；MAC 填错 |
| 平板息屏后过会儿失灵 | 没关电池优化 / 没执行 `termux-wake-lock` / 没开「充电保持唤醒」 |
| App 提示 token 校验失败 | 手机 token 与 `config.json` 不一致 |
| 开机后自动又关机 | BIOS 里 `ErP`/深度节能未关闭 |
| 手机浏览器访问 `/status` 返回 `{"ok":true}` | 说明手机↔平板链路通了，问题在平板→电脑这段（WoL/BIOS） |

> 提示：WoL 要求电脑处于**关机（软关机 S5）/睡眠/休眠**状态且网卡仍有待机供电。完全拔电源当然无法唤醒。
